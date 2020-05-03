from PySide2 import QtCore, QtUiTools
from PySide2.QtCore import QFile, QThreadPool
import asset_manager
import logging
from logging_extensions.QtTextLoggingHandler import QtTextLoggingHandler
from AppInfo import AppInfo
from PySide2.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class LoaderWindow(QtCore.QObject):
    def __init__(self, app : QApplication, appInfo : AppInfo, parentLogger : logging.Logger):
        super().__init__()
        self.app = app
        self.appInfo = appInfo
        
        file = QtCore.QFile(asset_manager.getUIFilePath("loader.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.window.setStyleSheet("background:transparent; border-image: url(./assets/images/bg.png) 0 0 0 0 stretch stretch;")
        self.window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.window.setFixedSize(300,100)
        self.window.statusLabel.setStyleSheet("QLabel { color : white; }")

        parentLogger.addHandler(QtTextLoggingHandler(self.window.statusLabel))

        self.window.show()
        self.window.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QtCore.QEvent.Close:
            self.quitApp()
            event.ignore()
            return True

        return super().eventFilter(obj, event)

    @QtCore.Slot()
    def quitApp(self, bSaveState = True):
        self.window.removeEventFilter(self)
        self.appInfo.applicationQuitting = True
        logger.info("Quitting application...")
        
        QtCore.QThreadPool.globalInstance().waitForDone()
        self.app.quit()