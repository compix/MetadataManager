from PySide2 import QtCore
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QProgressBar
import asset_manager

class ProgressDialog(object):
    def __init__(self, title: str = '') -> None:
        super().__init__()

        self.progressDialog = asset_manager.loadDialog('progressDialog.ui')
        self.progressDialog.setWindowFlags(self.progressDialog.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)
        self.progressDialog.setWindowTitle(title)

        self.progressBar: QProgressBar = self.progressDialog.progressBar
        self.progressBar.setMaximum(0)
        
    def setTitle(self, title: str):
        self.progressDialog.setWindowTitle(title)

    def updateProgress(self, progress: float, progressMessage: str = None):
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(int(round(progress * 100)))
        if progressMessage:
            self.progressDialog.infoLabel.setText(progressMessage)

        QtCore.QCoreApplication.processEvents()

    def open(self):
        self.progressDialog.show()
        QtCore.QCoreApplication.processEvents()

    def close(self):
        self.progressDialog.close()