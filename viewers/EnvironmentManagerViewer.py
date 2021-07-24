from viewers.EnvironmentViewer import EnvironmentViewer
from qt_extensions.DockWidget import DockWidget
from MetadataManagerCore.mongodb_manager import MongoDBManager
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QRegExp
from PySide2.QtGui import QRegExpValidator
from PySide2.QtWidgets import QMessageBox
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.environment.Environment import Environment
import logging

class EnvironmentManagerViewer(DockWidget):
    def __init__(self, parentWindow, environmentManager: EnvironmentManager, dbManager : MongoDBManager):
        super().__init__("Environment Manager", parentWindow, asset_manager.getUIFilePath("environmentManager.ui"))
        
        self.environmentManager : EnvironmentManager = environmentManager
        self.dbManager : MongoDBManager = dbManager

        self.environmentViewer = EnvironmentViewer(self.widget, environmentManager, dbManager)
        self.widget.environmentViewerLayout.addWidget(self.environmentViewer.widget)

        self.logger = logging.getLogger(__name__)

        self.environmentsComboBox : QtWidgets.QComboBox = self.widget.environmentsComboBox
        self.setupEnvironmentComboBox()

        self.widget.archiveEnvironmentButton.clicked.connect(self.onArchiveEnvironment)

        self.addMenuBar()
        self.refreshEnvironmentsComboBox()

        self.environmentManager.onStateChanged.subscribe(self.onEnvironmentManagerStateChanged)
        self.environmentViewer.onNewEnvironmentAdded.subscribe(lambda env: self.environmentsComboBox.addItem(env.displayName))

    def onEnvironmentManagerStateChanged(self):
        qt_util.runInMainThread(self.environmentViewer.updateSettingsTable)
        qt_util.runInMainThread(self.refreshEnvironmentsComboBox)

    def addMenuBar(self):
        menuBar = QtWidgets.QMenuBar()
        fileMenu = QtWidgets.QMenu("File")
        settingsMenu = QtWidgets.QMenu("Settings")

        menuBar.addMenu(fileMenu)
        menuBar.addMenu(settingsMenu)
        menuBar.setMaximumHeight(20)

        self.selectAutoExportPathAction = QtWidgets.QAction("Set Auto Export Path")
        self.selectAutoExportPathAction.triggered.connect(self.environmentViewer.openSelectAutoExportPathFileDialog)
        settingsMenu.addAction(self.selectAutoExportPathAction)

        self.importFromSettingsFileAction = QtWidgets.QAction("Import from Settings File")
        self.importFromSettingsFileAction.triggered.connect(self.environmentViewer.openImportFromSettingsFileDialog)
        fileMenu.addAction(self.importFromSettingsFileAction)

        self.exportAsJsonAction = QtWidgets.QAction("Export As Json")
        self.exportAsJsonAction.triggered.connect(self.environmentViewer.openExportAsJsonFileDialog)
        fileMenu.addAction(self.exportAsJsonAction)

        self.widget.layout().insertWidget(0, menuBar)

    def onArchiveEnvironment(self):
        if self.environmentViewer.environment != None and self.environmentManager.hasEnvironmentId(self.environmentViewer.environment.uniqueEnvironmentId):
            ret = QMessageBox.question(self, "Archive Environment", "Are you sure you want to archive the selected environment?")
            if ret == QMessageBox.Yes:
                self.environmentManager.archive(self.dbManager, self.environmentViewer.environment)
                self.refreshEnvironmentsComboBox()
                self.environmentsComboBox.setCurrentIndex(0)

    def setupEnvironmentComboBox(self):
        # Only allow alphabetic chars, digits, _, spaces:
        rx = QRegExp("[A-Za-z0-9 _]+")
        validator = QRegExpValidator(rx, self.widget)
        self.environmentsComboBox.setValidator(validator)

        self.environmentsComboBox.currentTextChanged.connect(self.onEnvironmentsComboBoxSelectedTextChanged)

    def onEnvironmentsComboBoxSelectedTextChanged(self, txt):
        potentialEnvironmentName = txt
        envId = self.environmentManager.getIdFromEnvironmentName(potentialEnvironmentName)
        env = self.environmentManager.getEnvironmentFromId(envId)
        if env != None:
            self.setCurrentEnvironment(env)
        else:
            env = Environment(envId)
            env.setDisplayName(potentialEnvironmentName)
            self.setCurrentEnvironment(env)

    def setCurrentEnvironment(self, env : Environment):
        if env.displayName != self.environmentsComboBox.currentText():
            self.environmentsComboBox.setCurrentText(env.displayName)
            
        self.environmentViewer.setEnvironment(env)

    def refreshEnvironmentsComboBox(self):
        curDisplayName = None
        if self.environmentViewer.environment:
            curDisplayName = self.environmentViewer.environment.displayName

        self.environmentsComboBox.clear()

        for env in self.environmentManager.environments:
            self.environmentsComboBox.addItem(env.displayName)

        if curDisplayName:
            self.environmentsComboBox.setCurrentText(curDisplayName)

    def saveState(self, settings: QtCore.QSettings):
        pass

    def restoreState(self, settings: QtCore.QSettings):
        pass