from logging import StreamHandler
from qt_extensions import qt_util

class QtTextLoggingHandler(StreamHandler):
    def __init__(self, textWidget):
        """
        The textWidget must have a textWidget.setText(str) function.
        """
        super().__init__()

        self.textWidget = textWidget

    def emit(self, record):
        msg = self.format(record)
        qt_util.runInMainThread(self.textWidget.setText, msg)