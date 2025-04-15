# spectrogram_view.py

import pyqtgraph as pg
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

class SpectrogramView(QMainWindow):
    """
    Displays a real-time rolling spectrogram via pyqtgraph.ImageView,
    with manual color scale levels using setLevels(minVal, maxVal).
    """

    def __init__(self, min_db=-80.0, max_db=0.0):
        """
        :param min_db: The lower bound (in dB) for the color scale
        :param max_db: The upper bound (in dB) for the color scale
        """
        super().__init__()
        self.setWindowTitle("bladeRF Real-Time Spectrogram (setLevels)")

        self.min_db = min_db
        self.max_db = max_db

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.image_view = pg.ImageView()
        layout.addWidget(self.image_view)

        # Unlock aspect ratio in the viewBox
        viewBox = self.image_view.getView()
        if viewBox is not None:
            viewBox.setAspectLocked(False)

        # We'll keep autoLevels=False so that setLevels() can work
        self.autoLevels = False

    def update_display(self, spectrogram_data):
        """
        1) Transpose the array for wide horizontal axis
        2) Display it with manual color levels
        """
        data_t = spectrogram_data.T

        # Update the image using fixed scaling
        self.image_view.setImage(
            data_t,
            autoLevels=self.autoLevels,    # keep it False or it will override
            autoRange=False,
            autoHistogramRange=False
        )

        # Now clamp the color scale to [min_db, max_db] dB
        self.image_view.setLevels(self.min_db, self.max_db)
