# views/spectrogram_view.py

import pyqtgraph as pg
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

class SpectrogramView(QMainWindow):
    """
    The GUI (View). Displays a real-time rolling spectrogram via pyqtgraph.ImageView.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("bladeRF Real-Time Spectrogram (MVC)")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # pyqtgraph.ImageView for our 2D spectrogram
        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)

    def update_display(self, spectrogram_data):
        """
        Given a 2D NumPy array (time/history axis x FFT bin axis),
        display it in the ImageView.
        """
        self.image_view.setImage(
            spectrogram_data,
            autoRange=False,
            autoLevels=False,
            autoHistogramRange=False
        )
