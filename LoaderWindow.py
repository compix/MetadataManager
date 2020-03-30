from PySide2 import QtCore, QtUiTools
from PySide2.QtCore import QFile, QTextStream, QThreadPool
import asset_manager
from MetadataManagerCore.mongodb_manager import MongoDBManager
from qt_extensions import qt_util
from time import sleep
from MainWindowManager import MainWindowManager

class LoaderWindow(QtCore.QObject):
    def __init__(self, app):
        super().__init__()
        self.applicationQuitting = False

        SETTINGS = QtCore.QSettings(asset_manager.getMainSettingsPath(), QtCore.QSettings.IniFormat)

        self.company = SETTINGS.value("company")
        self.appName = SETTINGS.value("app_name")
        self.mongodbHost = SETTINGS.value("mongodb_host")
        self.dbName = SETTINGS.value("db_name")

        self.app = app
        self.dbManager = None
        self.mainWindowManager = None
        
        file = QtCore.QFile(asset_manager.getUIFilePath("loader.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.window.setStyleSheet("background:transparent; border-image: url(./assets/images/bg.png) 0 0 0 0 stretch stretch;")
        self.window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.window.setFixedSize(300,100)
        self.window.statusLabel.setStyleSheet("QLabel { color : white; }")

        self.window.show()

        self.window.installEventFilter(self)

        #self.initDataBaseManager()
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.initDataBaseManager))

    def setupMainWindowManager(self):
        self.mainWindowManager = MainWindowManager(self.app, self.appName, self.company)
        self.mainWindowManager.setup(self.dbManager)
        self.mainWindowManager.show()

    def initDataBaseManager(self):
        connected = False
        self.dbManager = MongoDBManager(self.mongodbHost, self.dbName)

        while not connected:
            self.showMessage("Connecting to database...")

            try:
                self.dbManager.connect()
                self.showMessage("Connected.")
                qt_util.runInMainThread(self.setupMainWindowManager)
                connected = True
            except Exception as e:
                if self.applicationQuitting:
                    return

                print(f"Error: {str(e)}")
                sleep(2)
                self.showMessage("Failed to connect. Retrying...")
                sleep(1)
                continue

        qt_util.runInMainThread(self.window.hide)

    def showMessage(self, msg):
        print(msg)
        qt_util.runInMainThread(self.window.statusLabel.setText, msg)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QtCore.QEvent.Close:
            self.quitApp()
            event.ignore()
            return True

        return super().eventFilter(obj, event)

    @QtCore.Slot()
    def quitApp(self, bSaveState = True):
        self.window.removeEventFilter(self)
        self.applicationQuitting = True

        QtCore.QThreadPool.globalInstance().waitForDone()
        self.app.quit()