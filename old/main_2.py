#!/usr/bin/env python3

import sys
import numpy as np

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

import pyqtgraph as pg

import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32

class BladeRFHeatmap(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Minimal bladeRF Real-Time Heatmap (Fixed)")

        # -------------------------
        # 1) UI setup
        # -------------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)
        self.resize(800, 600)

        # -------------------------
        # 2) Open the first SoapySDR device
        # -------------------------
        print("[DEBUG] Enumerating devices...")
        self.sdr = SoapySDR.Device()
        print("[DEBUG] Opened device:", self.sdr)

        # Example config
        self.sample_rate = 2e6
        self.center_freq = 915e6
        self.gain        = 40

        self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.sdr.setGain(SOAPY_SDR_RX, 0, self.gain)

        # Create and activate RX stream
        self.rx_stream = self.sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
        self.sdr.activateStream(self.rx_stream)

        # -------------------------
        # 3) Spectrogram buffers
        # -------------------------
        self.fft_size = 1024
        self.spectrogram_history = 200
        # Rolling spectrogram data
        self.spectrogram_data = np.zeros((self.spectrogram_history, self.fft_size), dtype=np.float32)

        # -------------------------
        # 4) Timer for updates
        # -------------------------
        self.timer = QTimer()
        self.timer.setInterval(50)  # ~20 frames/sec
        self.timer.timeout.connect(self.update_spectrogram)
        self.timer.start()

    def update_spectrogram(self):
        """
        Periodically fetch samples, compute FFT, and update the image.
        Note: SoapySDR 0.8+ readStream() returns a StreamResult object, not a tuple.
        """
        num_samples = self.fft_size
        buff = np.empty(num_samples, dtype=np.complex64)

        # readStream() returns a "StreamResult" object
        # with attributes: .ret, .flags, .timeNs, etc.
        res = self.sdr.readStream(self.rx_stream, [buff], num_samples, timeoutUs=int(1e6))

        # status is the number of samples read or a negative error code
        status = res.ret
        flags  = res.flags
        timeNs = res.timeNs

        if status < 0:
            # Error from SoapySDR
            print(f"Error reading samples: status={status}")
            return

        if status == 0:
            # No samples read this iteration
            return

        samples_received = status  # Because .ret is actually "count of samples"
        samples = buff[:samples_received]

        # Compute a power spectrum from these samples
        power_spectrum = self.compute_power_spectrum(samples)

        # Scroll up and insert new row at the bottom
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
        # Apply a Hann window (optional)
        windowed = samples * np.hanning(len(samples))
        # FFT
        spectrum = np.fft.fftshift(np.fft.fft(windowed, self.fft_size))
        # Log-power
        return 20 * np.log10(np.abs(spectrum) + 1e-12)

    def closeEvent(self, event):
        """
        Cleanup streams on close.
        """
        self.sdr.deactivateStream(self.rx_stream)
        self.sdr.closeStream(self.rx_stream)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = BladeRFHeatmap()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
