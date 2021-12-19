from PySide2.QtGui import QMovie
from PySide2.QtWidgets import QPushButton

class LoadingButtonWrapper(object):
    def __init__(self, button: QPushButton) -> None:
        super().__init__()

        self.button = button
        self.originalIcon = self.button.icon()
        self.loadingMovie = QMovie(':/icons/eclipse_loading.gif')
    
    def startLoading(self):
        self.loadingMovie.start()
        self.loadingMovie.frameChanged.connect(self._onLoadingInProgressMovieFrameChanged)
        self.button.setEnabled(False)

    def stopLoading(self):
        self.loadingMovie.stop()
        self.loadingMovie.frameChanged.disconnect(self._onLoadingInProgressMovieFrameChanged)
        self.button.setIcon(self.originalIcon)
        self.button.setEnabled(True)

    def _onLoadingInProgressMovieFrameChanged(self, frame):
        self.button.setIcon(self.loadingMovie.currentPixmap())