from PySide2 import QtWidgets, QtCore, QtUiTools

class DockWidget(QtWidgets.QDockWidget):
    def __init__(self, title, parentWindow, uiFilePath):
        super().__init__(title, parentWindow)
        self.parentWindow = parentWindow
        self.title = title

        uiFile = QtCore.QFile(uiFilePath)
        uiFile.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.widget = loader.load(uiFile)

        self.setWidget(self.widget)
        self.setObjectName(f"{self.__class__.__name__}DockWidget")

    def saveState(self, settings: QtCore.QSettings):
        pass

    def restoreState(self, settings: QtCore.QSettings):
        pass