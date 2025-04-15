# main.py

import sys
from PyQt6.QtWidgets import QApplication
from models.sdr_model import SdrModel
from views.spectrogram_view import SpectrogramView
from controllers.spectrogram_controller import SpectrogramController

def main():
    # Create the Qt application
    app = QApplication(sys.argv)

    # Instantiate the MVC components
    model = SdrModel(sample_rate=2e6, freq=915e6, gain=40)
    view = SpectrogramView()
    controller = SpectrogramController(model, view, fft_size=1024, history=200)

    # Show the GUI
    view.show()
    # Start the spectrogram updates
    controller.start()

    # Run the Qt event loop
    exit_code = app.exec()

    # On exit, do cleanup
    controller.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
