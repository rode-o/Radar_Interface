# controllers/spectrogram_controller.py

import numpy as np
from PyQt6.QtCore import QTimer

class SpectrogramController:
    """
    Controller that ties the SdrModel (data) and the SpectrogramView (UI) together.
    It periodically reads data from the model, processes it (FFT), and updates the view.
    """

    def __init__(self, model, view, fft_size=1024, history=200):
        self.model = model
        self.view = view
        self.fft_size = fft_size

        # We'll store a rolling spectrogram of shape (history, fft_size).
        self.history = history
        self.spectrogram_data = np.zeros((history, fft_size), dtype=np.float32)

        # Create a QTimer to periodically update
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 updates/second
        self.timer.timeout.connect(self.update_spectrogram)

    def start(self):
        """
        Start the periodic updates.
        """
        self.timer.start()

    def stop(self):
        """
        Stop the periodic updates.
        """
        self.timer.stop()

    def update_spectrogram(self):
        """
        Periodic callback: read samples from the model, compute FFT,
        scroll the spectrogram buffer, and tell the view to update.
        """
        samples = self.model.read_samples(self.fft_size)
        if samples is None or len(samples) == 0:
            return

        # Compute power spectrum in dB
        power_spectrum = self._compute_power_spectrum(samples)

        # Scroll the old rows up
        self.spectrogram_data[:-1, :] = self.spectrogram_data[1:, :]
        # Insert the new row at the bottom
        self.spectrogram_data[-1, :] = power_spectrum

        # Update the view
        self.view.update_display(self.spectrogram_data)

    def _compute_power_spectrum(self, samples):
        """
        Apply a window function, compute FFT, return log-power (dB) spectrum.
        """
        window = np.hanning(len(samples))
        windowed = samples * window

        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        power_spectrum = 20 * np.log10(np.abs(spectrum) + 1e-12)
        return power_spectrum.astype(np.float32)

    def close(self):
        """
        Clean up resources if needed. Make sure we stop any timers and close the device.
        """
        self.stop()
        self.model.close()
