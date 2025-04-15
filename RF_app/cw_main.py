# cw_main.py

import sys
from PyQt6.QtWidgets import QApplication
from models.sdr_model import SdrModel
from views.spectrogram_view import SpectrogramView
from controllers.cw_doppler_controller import CW_DopplerController

def main():
    app = QApplication(sys.argv)

    model = SdrModel(sample_rate=520834, center_freq=915e6, rx_gain=40)

    view = SpectrogramView()

    controller = CW_DopplerController(
        model=model,
        view=view,
        sample_rate=520834,
        cw_freq_offset=0.0,
        fft_size=1024,
        history=200
    )

    view.show()
    controller.start()

    exit_code = app.exec()
    controller.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
