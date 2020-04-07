from qt_extensions.DockWidget import DockWidget
from MetadataManagerCore.mongodb_manager import MongoDBManager
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt, QRegExp
from PySide2.QtGui import QValidator, QRegExpValidator
from PySide2.QtWidgets import QMessageBox, QFileDialog
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.environment.Environment import Environment
from qt_extensions.SimpleTableModel import SimpleTableModel
import json, os
import subprocess

class EnvironmentManagerViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Environment Manager", parentWindow, asset_manager.getUIFilePath("environmentManager.ui"))
        
        self.autoExportPath : str = None
        self.environmentManager : EnvironmentManager = None
        self.dbManager : MongoDBManager = None

        self.widget.addButton.clicked.connect(self.onAddKeyValue)

        self.environmentsComboBox : QtWidgets.QComboBox = self.widget.environmentsComboBox
        self.setupEnvironmentComboBox()

        self.settingsTableView : QtWidgets.QTableView = self.widget.settingsTableView
        self.settingsTable = SimpleTableModel(self.settingsTableView, ["Key", "Value"])
        self.settingsTableView.setModel(self.settingsTable)

        self.currentEnvironment = None

        self.widget.archiveEnvironmentButton.clicked.connect(self.onArchiveEnvironment)

        self.widget.chooseFileButton.clicked.connect(self.onChooseFile)
        self.widget.chooseDirButton.clicked.connect(self.onChooseDir)

        self.settingsTableView.doubleClicked.connect(self.onTableViewDoubleClicked)

        self.widget.importFromSettingsFileButton.clicked.connect(self.onImportFromSettingsFile)
        self.widget.exportAsJsonButton.clicked.connect(self.onExportAsJson)
        self.widget.selectValueFileInExplorerButton.clicked.connect(self.onSelectValueFileInExplorerButton)
        self.widget.deleteEntryButton.clicked.connect(self.onDeleteEntry)

        self.addMenuBar()
        
    def onDeleteEntry(self):
        if self.currentEnvironment != None:
            key = self.widget.keyLineEdit.text()

            if key in self.currentEnvironment.settings:
                ret = QMessageBox.question(self, "Delete Entry", "Are you sure you want to delete the settings entry?")
                if ret == QMessageBox.Yes:
                    del self.currentEnvironment.settings[key]

                    for i in range(0, len(self.settingsTable.entries)):
                        existingTableKey = self.settingsTable.entries[i][0]
                        if existingTableKey == key:
                            self.settingsTable.removeRowAtIndex(i)
                            break

                    self.widget.deleteEntryButton.setEnabled(False)
                    self.saveEnvironment()

    def onSelectValueFileInExplorerButton(self):
        if os.name == 'nt':
            try:
                value = self.currentEnvironment.evaluateSettingsValue(self.widget.valueLineEdit.text())
                if os.path.exists(value):
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(value)}"')
            except Exception as e:
                print(e)

    def addMenuBar(self):
        menuBar = QtWidgets.QMenuBar()
        settingsMenu = QtWidgets.QMenu("Settings")

        menuBar.addMenu(settingsMenu)
        menuBar.setMaximumHeight(20)

        self.selectAutoExportPathAction = QtWidgets.QAction("Set Auto Export Path")
        self.selectAutoExportPathAction.triggered.connect(self.onSelectAutoExportPath)
        settingsMenu.addAction(self.selectAutoExportPathAction)

        self.widget.layout().insertWidget(0, menuBar)

    def onTableViewDoubleClicked(self, idx):
        entry = self.settingsTable.entries[idx.row()]
        self.widget.keyLineEdit.setText(entry[0])
        self.widget.valueLineEdit.setText(entry[1])

        value = self.currentEnvironment.evaluateSettingsValue(self.widget.valueLineEdit.text())
        self.widget.selectValueFileInExplorerButton.setEnabled(os.path.exists(value))

        self.widget.deleteEntryButton.setEnabled(True)

    def onChooseFile(self):
        fileName,_ = QFileDialog.getOpenFileName(self, "Open", "", "Any File (*.*)")
        if fileName != None and fileName != "":
            self.widget.valueLineEdit.setText(fileName)

    def onChooseDir(self):
        dirName = QFileDialog.getExistingDirectory(self, "Open", "")
        if dirName != None and dirName != "":
            self.widget.valueLineEdit.setText(dirName)

    def onArchiveEnvironment(self):
        if self.currentEnvironment != None and self.environmentManager.hasEnvironmentId(self.currentEnvironment.uniqueEnvironmentId):
            ret = QMessageBox.question(self, "Archive Environment", "Are you sure you want to archive the selected environment?")
            if ret == QMessageBox.Yes:
                self.environmentManager.archive(self.dbManager, self.currentEnvironment)
                self.environmentsComboBox.removeItem(self.environmentsComboBox.currentIndex())
                self.environmentsComboBox.setCurrentText("")
                self.settingsTable.clear()
        
    def setupKeyLineEdit(self):
        # Only allow alphabetic chars, digits, _, spaces:
        rx = QRegExp("[A-Za-z0-9 _]+")
        validator = QRegExpValidator(rx, self.widget)
        self.widget.keyLineEdit.setValidator(validator)
        
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

    def setup(self, environmentManager: EnvironmentManager, dbManager : MongoDBManager):
        self.environmentManager = environmentManager
        self.dbManager = dbManager

        self.refreshEnvironmentsComboBox()

    def saveEnvironment(self):
        if self.currentEnvironment != None and not self.environmentManager.hasEnvironmentId(self.currentEnvironment.uniqueEnvironmentId): 
            if self.environmentManager.isValidEnvironmentId(self.currentEnvironment.uniqueEnvironmentId):
                self.environmentManager.addEnvironment(self.currentEnvironment)
                self.environmentsComboBox.addItem(self.currentEnvironment.displayName)
            else:
                QMessageBox.warning("Invalid Environment Name", "Please enter a valid environment name.")

        self.environmentManager.save(self.dbManager)
        self.exportSettingsAsJson(self.autoExportPath)

    def setCurrentEnvironment(self, env : Environment):
        self.currentEnvironment = env
        
        self.settingsTable.clear()
        for key, val in env.settings.items():
            self.settingsTable.addEntry([key, val])

    def validateCurrentEnvironment(self):
        if self.currentEnvironment == None or not self.environmentManager.isValidEnvironmentId(self.currentEnvironment.uniqueEnvironmentId):
            QMessageBox.warning(self, "Invalid Environment Name", "Please enter a valid environment name.")
            return False

        return True

    def addEntry(self, key, value, save=True):
        """
        Adds a new entry or replaces an existing value if the key is already present in the settings dictionary.
        """
        if self.validateCurrentEnvironment():
            if key.strip() == "":
                QMessageBox.warning(self, "Invalid Key", "Please enter a valid key.")
                return False

            if not key in self.currentEnvironment.settings.keys():
                self.settingsTable.addEntry([key, value])
            else:
                for i in range(0, len(self.settingsTable.entries)):
                    existingTableKey = self.settingsTable.entries[i][0]
                    if existingTableKey == key:
                        self.settingsTable.replaceEntryAtRow(i, [key, value])
                        break
            
            self.widget.deleteEntryButton.setEnabled(True)
            self.currentEnvironment.settings[key] = value
            if save:
                self.saveEnvironment()
            return True
        else:
            return False

    def onAddKeyValue(self):
        key = self.widget.keyLineEdit.text()
        value = self.widget.valueLineEdit.text()
        self.addEntry(key, value)

    def refreshEnvironmentsComboBox(self):
        self.environmentsComboBox.clear()

        for env in self.environmentManager.environments:
            self.environmentsComboBox.addItem(env.displayName)

    def showItem(self, uid):
        form = self.widget.formLayout
        qt_util.clearContainer(form)
        item = self.dbManager.findOne(uid)
        if item != None:
            for key, val in item.items():
                valueEdit = QtWidgets.QLineEdit()
                valueEdit.setReadOnly(True)
                valueEdit.setText(str(val))
                valueEdit.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")
                form.addRow(str(key), valueEdit)
    
    def onImportFromSettingsFile(self):
        if not self.validateCurrentEnvironment():
            return

        filePath,_ = QFileDialog.getOpenFileName(self, "Open Settings File", "", "Any File (*.*)")

        if filePath != None and filePath != "":
            with open(filePath, 'r') as f:
                for line in f:
                    tokens = line.split("=")
                    
                    if len(tokens) == 2:
                        key = tokens[0].strip()
                        value = tokens[1].strip()

                        self.addEntry(key, value, save=False)

            self.saveEnvironment()

    def exportSettingsAsJson(self, filePath):
        if filePath != None and filePath != "" and os.path.exists(filePath):
            with open(filePath, 'w+') as f:
                json.dump(self.currentEnvironment.getEvaluatedSettings(), f, indent=4, sort_keys=True)

    def onExportAsJson(self):
        if not self.validateCurrentEnvironment():
            return

        filePath,_ = QFileDialog.getSaveFileName(self, "Save Settings As Json", "", "Any File (*.*)")
        self.exportSettingsAsJson(filePath)

    def onSelectAutoExportPath(self):
        filePath,_ = QFileDialog.getSaveFileName(self, "Save Settings As Json", "", "Any File (*.*)")

        if filePath != None and filePath != "":
            self.autoExportPath = filePath
            self.exportSettingsAsJson(filePath)
            self.saveEnvironment()

    def saveState(self, settings: QtCore.QSettings):
        settings.setValue("EnvironmentManagerViewer_AutoExportPath", self.autoExportPath)

    def restoreState(self, settings: QtCore.QSettings):
        self.autoExportPath = settings.value("EnvironmentManagerViewer_AutoExportPath")