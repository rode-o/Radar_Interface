# spectrogram.py

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

print("[DEBUG] Entered spectrogram.py...")

# Import our SDR interface
try:
    # Direct import from the same folder:
    from sdr_interface import BladeRFSdr
    print("[DEBUG] Imported BladeRFSdr from sdr_interface successfully.")
except Exception as e:
    print("[DEBUG] ERROR importing BladeRFSdr:", e)
    raise

class SpectrogramWindow(QMainWindow):
    def __init__(self, parent=None):
        print("[DEBUG] SpectrogramWindow.__init__ started...")
        super().__init__(parent)
        self.setWindowTitle("bladeRF Real-Time Spectrogram")

        # Main widget & layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # pyqtgraph ImageView for our spectrogram/heatmap
        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)

        print("[DEBUG] Creating BladeRFSdr() object...")
        self.sdr = BladeRFSdr(sample_rate=2e6, freq=915e6, gain=40)

        # Spectrogram parameters
        self.fft_size = 1024
        self.spectrogram_history = 200  # lines in the vertical/time axis
        self.spectrogram_data = np.zeros((self.spectrogram_history, self.fft_size), dtype=np.float32)

        # Set up a timer to periodically fetch new samples & update display
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 updates per second
        self.timer.timeout.connect(self.update_spectrogram)
        self.timer.start()

        print("[DEBUG] SpectrogramWindow.__init__ complete.")

    def update_spectrogram(self):
        """
        Called periodically by the timer. Fetch samples, compute FFT, update spectrogram array.
        """
        samples = self.sdr.read_samples(self.fft_size)
        if samples is None or len(samples) == 0:
            return

        power_spectrum = self.compute_power_spectrum(samples)

        # Scroll spectrogram data: move older lines up, add new line at the bottom
        self.spectrogram_data[:-1, :] = self.spectrogram_data[1:, :]
        self.spectrogram_data[-1, :] = power_spectrum

        # Update the image
        self.image_view.setImage(
            self.spectrogram_data,
            autoRange=False,
            autoLevels=False,
            autoHistogramRange=False
        )

    def compute_power_spectrum(self, samples):
        """
        Apply a window function, compute FFT, return log-power (dB) spectrum.
        """
        window = np.hanning(len(samples))
        windowed = samples * window

        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        power_spectrum = 20 * np.log10(np.abs(spectrum) + 1e-12)
        return power_spectrum

    def closeEvent(self, event):
        """
        Called when the window is closing. Cleanup the SDR before exit.
        """
        self.sdr.close()
        super().closeEvent(event)

print("[DEBUG] Done loading spectrogram.py!")
