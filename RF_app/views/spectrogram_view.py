# views/spectrogram_view.py

import pyqtgraph as pg
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

class SpectrogramView(QMainWindow):
    """
    The GUI (View). Knows how to display the spectrogram, but doesn't handle
    data acquisition or DSP directly. The Controller calls 'update_display()'
    with new data.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("bladeRF Real-Time Spectrogram (MVC)")

        # Main widget & layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # pyqtgraph ImageView to display our spectrogram
        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)

    def update_display(self, spectrogram_data):
        """
        Given a 2D NumPy array (time/history axis x frequency/FFT axis),
        display it in the ImageView.
        """
        self.image_view.setImage(
            spectrogram_data,
            autoRange=False,
            autoLevels=False,
            autoHistogramRange=False
        )
