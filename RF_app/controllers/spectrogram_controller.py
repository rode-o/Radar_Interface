# controllers/spectrogram_controller.py (simplified snippet)

import numpy as np
from PyQt6.QtCore import QTimer

class SpectrogramController:
    def __init__(self, model, view, fft_size=1024, history=200):
        self.model = model
        self.view = view
        self.fft_size = fft_size
        self.history = history
        self.spectrogram_data = np.zeros((history, fft_size), dtype=np.float32)

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._process_data)

    def start(self):
        # Start the radio threads
        self.model.start()
        # Start the GUI timer
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.model.stop()

    def _process_data(self):
        """
        Periodically check the RX queue for new blocks, do FFT, update spectrogram.
        """
        # We'll drain the queue so we keep up.
        while not self.model.rx_queue.empty():
            block = self.model.rx_queue.get()
            if block is not None and len(block) > 0:
                # Perform FFT or correlation, etc.
                psd = self._compute_psd(block)
                # Scroll spectrogram
                self.spectrogram_data[:-1, :] = self.spectrogram_data[1:, :]
                self.spectrogram_data[-1, :] = psd
                # Update view
                self.view.update_display(self.spectrogram_data)

    def _compute_psd(self, samples):
        window = np.hanning(len(samples))
        windowed = samples * window
        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        power = 20 * np.log10(np.abs(spectrum)+1e-12)
        return power.astype(np.float32)
