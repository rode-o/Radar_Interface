# controllers/spectrogram_controller.py

import numpy as np
from PyQt6.QtCore import QTimer

class SpectrogramController:
    """
    Periodically fetches blocks from SdrModel, applies optional software DC removal,
    does FFT, updates spectrogram.
    """

    def __init__(
        self,
        model,
        view,
        fft_size=1024,
        history=200,
        mean_subtraction=False,
        iir_dc_block=False
    ):
        self.model = model
        self.view = view
        self.fft_size = fft_size
        self.history = history

        # Two software DC solutions:
        self.mean_subtraction = mean_subtraction
        self.iir_dc_block = iir_dc_block

        # For an IIR high-pass approach, store a small "dc_state"
        self.dc_alpha = 0.99  # close to 1 => slow adapt
        self.dc_state = 0.0 + 0j

        self.spectrogram_data = np.zeros((history, fft_size), dtype=np.float32)

        self.timer = QTimer()
        self.timer.setInterval(1)
        self.timer.timeout.connect(self._process_data)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def close(self):
        self.stop()
        self.model.close()

    def _process_data(self):
        samples = self.model.read_samples(self.fft_size)
        if samples is None or len(samples) == 0:
            return

        # Option A: Subtract block mean
        if self.mean_subtraction:
            block_mean = np.mean(samples)
            samples = samples - block_mean

        # Option B: IIR-based DC removal
        # (slowly adapt, removing near DC)
        if self.iir_dc_block:
            # y[n] = x[n] - dc_state
            # dc_state = alpha*dc_state + (1-alpha)*x[n]
            # approach for each sample
            new_block = np.empty_like(samples)
            for i in range(len(samples)):
                new_block[i] = samples[i] - self.dc_state
                self.dc_state = self.dc_alpha*self.dc_state + (1-self.dc_alpha)*samples[i]
            samples = new_block

        # Compute power spectrum
        power_spectrum = self._compute_power_spectrum(samples)

        # Scroll
        self.spectrogram_data[:-1, :] = self.spectrogram_data[1:, :]
        self.spectrogram_data[-1, :] = power_spectrum

        self.view.update_display(self.spectrogram_data)

    def _compute_power_spectrum(self, samples):
        window = np.hanning(len(samples))
        windowed = samples * window
        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        power_spectrum = 20 * np.log10(np.abs(spectrum) + 1e-12)
        return power_spectrum.astype(np.float32)
