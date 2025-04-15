# sdr_model.py

import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_TX, SOAPY_SDR_CF32
import numpy as np
import threading
import queue
import time

class SdrModel:
    """
    Manages bladeRF (or any SoapySDR device) for continuous TX and RX.
    Spawns separate threads for reading/writing streams to avoid data loss.
    """

    def __init__(self, sample_rate=1e6, center_freq=915e6, rx_gain=40, tx_gain=30):
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.rx_gain = rx_gain
        self.tx_gain = tx_gain

        print("[INFO] Opening SoapySDR Device (no args) for bladeRF...")
        self.dev = SoapySDR.Device()  # no-arg => first enumerated device

        # --- Configure RX channel ---
        self.dev.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
        self.dev.setFrequency(SOAPY_SDR_RX, 0, self.center_freq)
        self.dev.setGain(SOAPY_SDR_RX, 0, self.rx_gain)

        # --- Configure TX channel ---
        self.dev.setSampleRate(SOAPY_SDR_TX, 0, self.sample_rate)
        self.dev.setFrequency(SOAPY_SDR_TX, 0, self.center_freq)
        self.dev.setGain(SOAPY_SDR_TX, 0, self.tx_gain)

        # --- Setup streams ---
        self.rx_stream = self.dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
        self.tx_stream = self.dev.setupStream(SOAPY_SDR_TX, SOAPY_SDR_CF32, [0])

        # --- Activate streams (continuous) ---
        self.dev.activateStream(self.rx_stream)
        self.dev.activateStream(self.tx_stream)

        # --- Thread management ---
        self.rx_thread = None
        self.tx_thread = None
        self.stop_flag = threading.Event()

        # A queue to hold incoming samples for the DSP or GUI
        self.rx_queue = queue.Queue()

    def start(self):
        """
        Start the RX and TX threads.
        """
        self.stop_flag.clear()

        # RX Thread: continuous read
        self.rx_thread = threading.Thread(target=self._rx_worker, args=(), daemon=True)
        self.rx_thread.start()

        # TX Thread: continuous write of a test waveform (example)
        self.tx_thread = threading.Thread(target=self._tx_worker, args=(), daemon=True)
        self.tx_thread.start()

        print("[INFO] RX and TX threads started.")

    def stop(self):
        """
        Signal threads to stop and wait for them to join.
        """
        self.stop_flag.set()

        # Wait for threads to exit
        if self.rx_thread is not None:
            self.rx_thread.join()
        if self.tx_thread is not None:
            self.tx_thread.join()

        print("[INFO] RX and TX threads stopped.")

    def close(self):
        """
        Deactivate and close streams, device, etc.
        """
        self.stop()
        self.dev.deactivateStream(self.rx_stream)
        self.dev.closeStream(self.rx_stream)
        self.dev.deactivateStream(self.tx_stream)
        self.dev.closeStream(self.tx_stream)

    def _rx_worker(self):
        """
        RX thread function: continuous readStream() calls, push data into a queue.
        """
        read_size = 1024
        rx_buff = np.zeros(read_size, dtype=np.complex64)

        while not self.stop_flag.is_set():
            sr = self.dev.readStream(self.rx_stream, [rx_buff], read_size, timeoutUs=100000)
            status = sr.ret

            if status > 0:
                # Slice out the valid portion
                num_rx_samps = status
                data_chunk = rx_buff[:num_rx_samps].copy()
                # Put it into the queue for processing
                self.rx_queue.put(data_chunk)
            elif status == 0:
                # No samples, just sleep a bit
                time.sleep(0.001)
            else:
                # Error (overflow is typically -4)
                print(f"[WARN] RX stream error: {status}")
                time.sleep(0.01)

    def _tx_worker(self):
        """
        TX thread function: continuously writes a waveform to keep the TX pipeline running.
        This is just an example (a simple tone or zero).
        """
        tone_freq = 10e3  # 10 kHz test tone, for example
        tx_size = 1024
        sample_period = 1.0 / self.sample_rate

        # Generate or continuously generate a tone
        phase_acc = 0.0
        while not self.stop_flag.is_set():
            t = np.arange(tx_size) * sample_period
            wave = np.exp(1j * 2 * np.pi * tone_freq * t + phase_acc)

            # Update phase for next block
            phase_acc += 2 * np.pi * tone_freq * tx_size * sample_period

            # Write to TX stream
            sr = self.dev.writeStream(self.tx_stream, [wave.astype(np.complex64)], tx_size)
            if sr.ret < 0:
                print(f"[WARN] TX write error: {sr.ret}")
                time.sleep(0.01)
