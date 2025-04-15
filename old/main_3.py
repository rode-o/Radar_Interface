#!/usr/bin/env python3

"""
bladeRF Pulse Radar w/ Heatmap (Snapshot Mode)
---------------------------------------------
1) Sample rate ~520.834 kHz
2) RX buffer = 256 samples
3) Timer interval = 500 ms (2 FPS)
4) Snapshot approach: Activate/Deactivate Rx each read

This drastically reduces data throughput. Each timer tick:
 - Activate RX for a single burst (256 samples)
 - Deactivate RX
 - Correlate + update heatmap

You won't get continuous data, but it should avoid 'RX error: -4'.
"""

import sys
import numpy as np

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer

import pyqtgraph as pg

import SoapySDR
from SoapySDR import SOAPY_SDR_TX, SOAPY_SDR_RX, SOAPY_SDR_CF32

SPEED_OF_LIGHT = 3e8

class BladeRFRadarHeatmap(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("bladeRF Radar Heatmap (Snapshot Mode)")

        # ----- GUI Setup -----
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)

        # ----- SoapySDR Setup -----
        print("[INFO] Opening first SoapySDR device...")
        self.sdr = SoapySDR.Device()

        # Target sample rate ~ 520.834 kHz
        self.sample_rate = 520834.0
        self.center_freq = 2.4e9
        self.tx_gain     = 30
        self.rx_gain     = 40

        print(f"[INFO] Setting sample rate to {self.sample_rate} Hz (~{self.sample_rate/1e6:.6f} MHz)")

        # TX Config
        self.sdr.setSampleRate(SOAPY_SDR_TX, 0, self.sample_rate)
        self.sdr.setFrequency(SOAPY_SDR_TX, 0, self.center_freq)
        self.sdr.setGain(SOAPY_SDR_TX, 0, self.tx_gain)

        # We'll set up a TX stream once, but we'll only write occasionally
        self.tx_stream = self.sdr.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32, [0])
        self.sdr.activateStream(self.tx_stream)

        # RX Config
        # We won't keep this stream active the whole time, we'll do snapshot.
        self.sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.sdr.setGain(SOAPY_SDR_RX, 0, self.rx_gain)

        # Generate a short pulse
        self.pulse = make_pulse(self.sample_rate, pulse_width_us=10)
        self.pulse_len = len(self.pulse)
        print(f"[INFO] Pulse length: {self.pulse_len} samples")

        # TX buffer = 256
        self.tx_buf_len = 256
        self.tx_buffer  = np.zeros(self.tx_buf_len, dtype=np.complex64)
        self.tx_buffer[:self.pulse_len] = self.pulse

        # We'll do snapshot reads of 256 samples
        self.rx_buf_len = 256
        self.rx_buffer  = np.zeros(self.rx_buf_len, dtype=np.complex64)

        # The correlation length => 256 + pulse_len - 1
        self.corr_len = self.rx_buf_len + self.pulse_len - 1
        print(f"[INFO] Correlation length: {self.corr_len}")

        # Heatmap rolling buffer
        self.heatmap_height = 200
        self.heatmap_data = np.zeros((self.heatmap_height, self.corr_len), dtype=np.float32)

        # Timer: 500 ms => ~2 FPS
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.radar_update)
        self.timer.start()

        self.show()

    def radar_update(self):
        """Snapshot approach: 
           1) TX one buffer
           2) Activate + read one burst on RX, then deactivate
           3) Correlate + update heatmap
        """

        # ----- TRANSMIT ----- (one pulse buffer)
        txr = self.sdr.writeStream(self.tx_stream, [self.tx_buffer], self.tx_buf_len)
        if txr.ret < 0:
            print(f"[WARN] TX error: {txr.ret}")

        # ----- SNAPSHOT RX -----
        #  1) Setup + activate the RX stream each time
        self.rx_stream = self.sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
        self.sdr.activateStream(self.rx_stream)

        #  2) Read once
        rxr = self.sdr.readStream(self.rx_stream, [self.rx_buffer], self.rx_buf_len, timeoutUs=int(1e5))
        self.sdr.deactivateStream(self.rx_stream)
        self.sdr.closeStream(self.rx_stream)

        if rxr.ret < 0:
            print(f"[WARN] RX error: {rxr.ret}")
            return
        num_rx_samps = rxr.ret
        if num_rx_samps == 0:
            return

        rx_samples = self.rx_buffer[:num_rx_samps]

        # ----- CORRELATE -----
        corr = np.correlate(rx_samples, self.pulse, mode='full')
        corr_mag = np.abs(corr)

        # Pad/clip to corr_len
        if len(corr_mag) < self.corr_len:
            row_data = np.zeros(self.corr_len, dtype=np.float32)
            row_data[:len(corr_mag)] = corr_mag
        else:
            row_data = corr_mag[:self.corr_len].astype(np.float32)

        # ----- Shift Heatmap + Insert New Row -----
        self.heatmap_data[:-1, :] = self.heatmap_data[1:, :]
        self.heatmap_data[-1, :]  = row_data

        # ----- Update Image -----
        self.image_view.setImage(
            self.heatmap_data,
            autoLevels=False,
            autoRange=False,
            autoHistogramRange=False
        )

    def closeEvent(self, event):
        """Cleanup on window close."""
        # Deactivate/close TX
        self.sdr.deactivateStream(self.tx_stream)
        self.sdr.closeStream(self.tx_stream)
        super().closeEvent(event)

def make_pulse(sample_rate, pulse_width_us=10, freq_offset=0):
    """Generate a short, windowed baseband pulse."""
    pulse_len = int(sample_rate * (pulse_width_us * 1e-6))
    t = np.arange(pulse_len) / sample_rate
    sig = np.exp(1j * 2*np.pi * freq_offset * t)
    window = np.hanning(pulse_len)
    pulse = sig * window
    return pulse.astype(np.complex64)

def main():
    app = QApplication(sys.argv)
    w = BladeRFRadarHeatmap()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
