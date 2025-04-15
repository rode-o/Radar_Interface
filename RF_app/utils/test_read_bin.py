#!/usr/bin/env python3

"""
Reads a binary file of SC16 Q11 IQ samples ("test_samples.bin"), applies a
basic DC offset correction by subtracting the mean, and plots a spectrogram
using matplotlib.

Usage (from RF_app folder):
    python ./utils/test_read_bin.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Adjust if your file name or path differ
    filename = os.path.join("data", "test_samples.bin")
    
    # The number of complex samples we expect (from bladeRF-cli: n=100000)
    num_samples = 100000

    # SC16 Q11 => each complex sample = 4 bytes => 400kB for 100k samples
    file_size = os.path.getsize(filename)
    expected_size = num_samples * 4
    if file_size != expected_size:
        print(f"[WARN] File size ({file_size} bytes) != expected ({expected_size} bytes).")

    # Read raw int16 data into a NumPy array: length = 2*num_samples
    raw_data = np.fromfile(filename, dtype=np.int16, count=num_samples * 2)
    if len(raw_data) < 2 * num_samples:
        print(f"[WARN] Only read {len(raw_data)} int16s, expected {2*num_samples}.")

    # Separate I (even) and Q (odd) samples
    i_vals = raw_data[0::2]
    q_vals = raw_data[1::2]

    # Convert from Q11 fixed-point => float (divide by 2^11 = 2048)
    iq_complex = (i_vals + 1j * q_vals) / 2048.0

    print(f"[INFO] Loaded {iq_complex.size} IQ samples from: {filename}")
    print("[INFO] Example amplitude stats:",
          f"mean={np.mean(np.abs(iq_complex)):.3f},",
          f"max={np.max(np.abs(iq_complex)):.3f}")

    # ----- Software DC offset removal -----
    # Subtract the mean from the time-domain samples.
    # This is a simple high-pass approach that removes DC.
    dc_mean = np.mean(iq_complex)
    iq_corrected = iq_complex - dc_mean
    print(f"[INFO] DC offset (mean) was {dc_mean.real:.6f} + j{dc_mean.imag:.6f}")

    # We'll assume a sample rate ~1 MHz from your bladeRF capture
    sample_rate = 1.0e6  # Hz

    # Plot a spectrogram with matplotlib
    fig, ax = plt.subplots(figsize=(10, 6))

    # We'll do an STFT with NFFT=1024, overlap=512, scale in dB
    nfft = 1024
    noverlap = 512
    spec_power, freqs, t_bins, im = ax.specgram(
        x=iq_corrected,      # use the corrected samples
        NFFT=nfft,
        Fs=sample_rate,
        noverlap=noverlap,
        scale='dB'
    )

    ax.set_title("Spectrogram of Captured bladeRF Data (DC-corrected)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Frequency (Hz)")
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Power (dB)")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
