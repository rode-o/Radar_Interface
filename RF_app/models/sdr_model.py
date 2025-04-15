# models/sdr_model.py

import SoapySDR
from SoapySDR import *  # SOAPY_SDR_* constants
import numpy as np

class SdrModel:
    """
    Encapsulates the bladeRF (or any SoapySDR device) configuration and
    provides a method for reading samples.
    """

    def __init__(self, sample_rate=2e6, freq=915e6, gain=40):
        """
        Initialize the SoapySDR device for bladeRF, configuring sample rate,
        frequency, and gain. Creates and activates an RX stream.
        """
        # Enumerate SoapySDR devices
        dev_infos = SoapySDR.Device.enumerate()
        if not dev_infos:
            raise RuntimeError("No SoapySDR devices found at all!")

        # Look for a device whose driver is bladeRF
        bladeRfInfo = None
        for info in dev_infos:
            d = dict(info)
            if d.get("driver") == "bladerf":
                bladeRfInfo = d
                break

        if bladeRfInfo is None:
            raise RuntimeError("No bladeRF device found in SoapySDR enumeration!")

        # Open the device
        self.dev = SoapySDR.Device(bladeRfInfo)

        # Configure RX
        self.dev.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
        self.dev.setFrequency(SOAPY_SDR_RX, 0, freq)
        self.dev.setGain(SOAPY_SDR_RX, 0, gain)

        # Setup RX stream
        self.rx_stream = self.dev.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32, [0])
        self.dev.activateStream(self.rx_stream)

        self.sample_rate = sample_rate
        self.freq = freq
        self.gain = gain

    def read_samples(self, num_samples=1024):
        """
        Read a block of IQ samples (complex float32).
        Returns a NumPy array of shape (num_samples,) or None on error.
        """
        buff = np.zeros(num_samples, dtype=np.complex64)
        sr = self.dev.readStream(self.rx_stream, [buff], num_samples, timeoutUs=int(1e6))

        status = sr.ret
        if status < 0:
            print(f"[SdrModel] Error reading samples: status={status}")
            return None
        samples_received = status
        return buff[:samples_received]

    def close(self):
        """
        Deactivate and close the SoapySDR stream; call this before exiting.
        """
        self.dev.deactivateStream(self.rx_stream)
        self.dev.closeStream(self.rx_stream)
