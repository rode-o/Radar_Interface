# models/sdr_model.py

import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_TX
import numpy as np
import threading
import queue
import time
import subprocess

class SdrModel:
    """
    Multi-threaded bladeRF Soapy model with optional hardware calibrations.
    """

    def __init__(
        self,
        sample_rate=520834,
        center_freq=2.4e9,
        rx_gain=40,
        tx_gain=30,
        hardware_cal=False
    ):
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.rx_gain = rx_gain
        self.tx_gain = tx_gain
        self.hardware_cal = hardware_cal

        print("[INFO] Opening SoapySDR Device (no args) for bladeRF...")
        self.dev = SoapySDR.Device()

        # Configure RX
        self.dev.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.dev.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.dev.setGain(SOAPY_SDR_RX, 0, self.rx_gain)

        # Configure TX
        self.dev.setSampleRate(SOAPY_SDR_TX, 0, self.sample_rate)
        self.dev.setFrequency(SOAPY_SDR_TX, 0, self.center_freq)
        self.dev.setGain(SOAPY_SDR_TX, 0, self.tx_gain)

        # Setup streams
        self.rx_stream = self.dev.setupStream(SOAPY_SDR_RX, "CF32", [0])
        self.tx_stream = self.dev.setupStream(SOAPY_SDR_TX, "CF32", [0])
        self.dev.activateStream(self.rx_stream)
        self.dev.activateStream(self.tx_stream)

        self.stop_flag = threading.Event()
        self.rx_queue = queue.Queue()

        self.rx_thread = None
        self.tx_thread = None

        # Start threads
        self.start()

        # Attempt hardware DC calibrations if requested
        if self.hardware_cal:
            self._attempt_hardware_dc_cal()

    def _attempt_hardware_dc_cal(self):
        print("[INFO] Attempting hardware DC calibration...")

        # Approach A: Soapy-level setting
        try:
            self.dev.writeSetting("CALIBRATE_DC_RX", "")
            print("[INFO] Soapy: CALIBRATE_DC_RX succeeded.")
        except Exception as ex:
            print(f"[WARN] Soapy CALIBRATE_DC_RX failed: {ex}")

        # Approach B: bladeRF-cli
        # This often fails if the device is in use by Soapy. Just a demonstration.
        try:
            result = subprocess.run(
                ["bladeRF-cli", "-c", "calibrate dc rx"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("[INFO] bladeRF-cli calibrate dc rx success")
            else:
                print("[WARN] bladeRF-cli calibrate dc rx returned error:")
                print(result.stdout, result.stderr)
        except FileNotFoundError:
            print("[WARN] bladeRF-cli not found in PATH.")
        except Exception as e:
            print(f"[WARN] External calibrate command failed: {e}")

    def start(self):
        """Start the RX and TX streaming threads."""
        self.stop_flag.clear()

        self.rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
        self.rx_thread.start()

        self.tx_thread = threading.Thread(target=self._tx_worker, daemon=True)
        self.tx_thread.start()

        print("[INFO] RX and TX threads started.")

    def stop(self):
        """Stop the worker threads."""
        self.stop_flag.set()
        if self.rx_thread:
            self.rx_thread.join()
        if self.tx_thread:
            self.tx_thread.join()
        print("[INFO] RX and TX threads stopped.")

    def close(self):
        """Deactivate streams, close device."""
        self.stop()
        self.dev.deactivateStream(self.rx_stream)
        self.dev.closeStream(self.rx_stream)
        self.dev.deactivateStream(self.tx_stream)
        self.dev.closeStream(self.tx_stream)
        print("[INFO] bladerf_close() done.")

    def _rx_worker(self):
        read_size = 1024
        rx_buff = np.zeros(read_size, dtype=np.complex64)
        while not self.stop_flag.is_set():
            sr = self.dev.readStream(self.rx_stream, [rx_buff], read_size, timeoutUs=100000)
            status = sr.ret
            if status > 0:
                data_chunk = rx_buff[:status].copy()
                self.rx_queue.put(data_chunk)
            elif status == 0:
                time.sleep(0.001)
            else:
                print(f"[WARN] RX stream error: {status}")
                time.sleep(0.01)

    def _tx_worker(self):
        tone_freq = 10e3
        tx_size = 1024
        sample_period = 1.0 / self.sample_rate
        phase_acc = 0.0

        while not self.stop_flag.is_set():
            t = np.arange(tx_size) * sample_period
            wave = np.exp(1j * (2*np.pi*tone_freq*t + phase_acc))

            phase_inc = 2 * np.pi * tone_freq * tx_size * sample_period
            phase_acc = (phase_acc + phase_inc) % (2*np.pi)

            wave_32 = wave.astype(np.complex64)
            sr = self.dev.writeStream(self.tx_stream, [wave_32], tx_size)
            if sr.ret < 0:
                print(f"[WARN] TX write error: {sr.ret}")
                time.sleep(0.01)

    def read_samples(self, num_samples=1024):
        """
        Non-blocking get from rx_queue. Returns None if empty.
        """
        import queue
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None
