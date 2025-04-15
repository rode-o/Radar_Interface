# main.py

import sys
from PyQt6.QtWidgets import QApplication
from models.sdr_model import SdrModel
from views.spectrogram_view import SpectrogramView
from controllers.spectrogram_controller import SpectrogramController

def main():
    app = QApplication(sys.argv)

    # Create the model at ~520.834 kHz
    # hardware_cal=True => attempt Soapy+bladeRF-cli calibrations on init
    model = SdrModel(
        sample_rate=520834,
        center_freq=915e6,
        rx_gain=40,
        tx_gain=30,
        hardware_cal=True
    )

    view = SpectrogramView()

    # Create the controller with software solutions:
    # 1) mean_subtraction=True => subtract block mean each chunk
    # 2) iir_dc_block=True => use a slow high-pass filter approach
    # In practice, pick one or the other
    controller = SpectrogramController(
        model=model,
        view=view,
        fft_size=2048,
        history=200,
        mean_subtraction=True,  # enable/disable as desired
        iir_dc_block=False      # alternative approach
    )

    view.show()
    view.showMaximized()
    controller.start()

    exit_code = app.exec()

    controller.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
