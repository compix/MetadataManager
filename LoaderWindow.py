from PySide2 import QtCore, QtUiTools
from PySide2.QtCore import QFile, QTextStream, QThreadPool
import asset_manager
from MetadataManagerCore.mongodb_manager import MongoDBManager
from qt_extensions import qt_util
from time import sleep

class LoaderWindow(QtCore.QObject):
    def __init__(self, app, mainWindowManager, mongodbHost, dbName):
        self.app = app
        self.dbManager = None
        self.mongodbHost = mongodbHost
        self.dbName = dbName
        self.mainWindowManager = mainWindowManager
        
        file = QtCore.QFile(asset_manager.getUIFilePath("loader.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)
        #self.window.setParent(mainWindow.window)

        self.window.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.window.setStyleSheet("background:transparent; border-image: url(./assets/images/bg.png) 0 0 0 0 stretch stretch;")
        self.window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.window.setFixedSize(300,100)
        self.window.show()

        #self.initDataBaseManager()
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.initDataBaseManager))

    def initDataBaseManager(self):
        connected = False
        self.dbManager = MongoDBManager(self.mongodbHost, self.dbName)

        while not connected:
            self.showMessage("Connecting to database...")

            try:
                self.dbManager.connect()
                self.showMessage("Connected.")
                qt_util.runInMainThread(self.mainWindowManager.setup, self.dbManager)
                qt_util.runInMainThread(self.mainWindowManager.show)
                connected = True
            except Exception as e:
                print(f"Error: {str(e)}")
                sleep(2)
                self.showMessage("Failed to connect. Retrying...")
                sleep(1)
                continue

        qt_util.runInMainThread(self.window.hide)

    def showMessage(self, msg):
        print(msg)
        qt_util.runInMainThread(self.window.statusLabel.setText, msg)