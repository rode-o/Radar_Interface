# main.py

import sys
from PyQt6.QtWidgets import QApplication
from models.sdr_model import SdrModel
from views.spectrogram_view import SpectrogramView
from controllers.spectrogram_controller import SpectrogramController

def main():
    app = QApplication(sys.argv)

    # Instantiate Model, View, Controller
    model = SdrModel(sample_rate=2e6, center_freq=915e6, rx_gain=40)
    view = SpectrogramView()
    controller = SpectrogramController(model, view, fft_size=1024, history=200)

    # Show the GUI and start streaming
    view.show()
    controller.start()

    # Run the Qt event loop
    exit_code = app.exec()

    # Cleanup
    controller.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
