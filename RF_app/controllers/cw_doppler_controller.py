# controllers/cw_doppler_controller.py

import numpy as np
from PyQt6.QtCore import QTimer

class CW_DopplerController:
    """
    A specialized controller for CW radar Doppler detection.
    1) Mix the received IQ with a reference tone at f0 (software mixer).
    2) Low-pass or decimate.
    3) Display a narrow FFT focusing on low-frequency Doppler.

    Debugging additions:
      - Print out sample lengths and min/max to ensure data is being read
      - Check if block is empty or all zero
    """

    def __init__(
        self,
        model,
        view,
        sample_rate=520834,   # The raw wide sample rate
        cw_freq_offset=0.0,   # offset from center freq
        fft_size=2048,
        history=200
    ):
        self.model = model
        self.view = view

        self.raw_sample_rate = sample_rate
        self.cw_freq_offset = cw_freq_offset
        self.fft_size = fft_size
        self.history = history

        # We'll store a spectrogram of shape (history, fft_size),
        # but it is the "baseband" doppler spectrum now
        self.spectrogram_data = np.zeros((history, fft_size), dtype=np.float32)

        # We choose a smaller final sample rate after mixing + decim
        self.doppler_rate = 2000.0  # ~2 kHz
        self.decimation = int(self.raw_sample_rate / self.doppler_rate)
        if self.decimation < 1:
            self.decimation = 1
        print(f"[INFO] Doppler decimation factor: {self.decimation}")

        # Timer for GUI update
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 fps
        self.timer.timeout.connect(self._process_data)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def close(self):
        self.stop()
        self.model.close()

    def _process_data(self):
        """
        We'll read a chunk from the queue, do software mix, decimate,
        then an FFT to see the Doppler band near DC.
        """
        block_size = 4096
        samples = self.model.read_samples(block_size)
        if samples is None or len(samples) == 0:
            # Debug print if empty
            print("[DEBUG] No new samples (None or zero-length).")
            return

        # Debug: print basic info about raw samples
        print(f"[DEBUG] Got {len(samples)} samples from read_samples().")
        print(f"[DEBUG] min/max real part: {samples.real.min():.3f} / {samples.real.max():.3f}")

        # 1) Software mix => e^-j(2pi f_offset t)
        t = np.arange(len(samples)) / self.raw_sample_rate
        mix_signal = np.exp(-1j * 2*np.pi*self.cw_freq_offset * t)
        mixed = samples * mix_signal

        # 2) Decimate
        decimated = mixed[::self.decimation]
        decim_rate = self.raw_sample_rate / self.decimation

        # 3) (Optional) low-pass filter => omitted for simplicity

        # 4) If we have enough samples for the FFT
        if len(decimated) < self.fft_size:
            print(f"[DEBUG] decimated length={len(decimated)} < fft_size={self.fft_size}, skipping.")
            return

        data_block = decimated[:self.fft_size]

        # Subtract DC from this block
        data_block -= np.mean(data_block)

        # Window + FFT
        window = np.hanning(len(data_block))
        windowed = data_block * window
        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        power_spectrum = 20 * np.log10(np.abs(spectrum) + 1e-12).astype(np.float32)

        # Debug: check range of power_spectrum
        ps_min, ps_max = float(power_spectrum.min()), float(power_spectrum.max())
        print(f"[DEBUG] power_spectrum range: {ps_min:.2f} dB to {ps_max:.2f} dB")

        # Insert row into spectrogram
        self.spectrogram_data[:-1, :] = self.spectrogram_data[1:, :]
        self.spectrogram_data[-1, :] = power_spectrum

        # Update
        self.view.update_display(self.spectrogram_data)
