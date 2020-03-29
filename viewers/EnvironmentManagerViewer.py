from qt_extensions.DockWidget import DockWidget
from MetadataManagerCore.mongodb_manager import MongoDBManager
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt, QRegExp
from PySide2.QtGui import QValidator, QRegExpValidator
from PySide2.QtWidgets import QMessageBox, QFileDialog
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.environment.Environment import Environment
from qt_extensions.SimpleTableModel import SimpleTableModel

class EnvironmentManagerViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Environment Manager", parentWindow, asset_manager.getUIFilePath("environmentManager.ui"))
        
        self.environmentManager : EnvironmentManager = None
        self.dbManager : MongoDBManager = None

        self.widget.addButton.clicked.connect(self.onAddKeyValue)
        self.widget.saveButton.clicked.connect(self.onSave)

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
        
    def onTableViewDoubleClicked(self, idx):
        entry = self.settingsTable.entries[idx.row()]
        self.widget.keyLineEdit.setText(entry[0])
        self.widget.valueLineEdit.setText(entry[1])

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

    def onSave(self):
        if self.currentEnvironment != None and not self.environmentManager.hasEnvironmentId(self.currentEnvironment.uniqueEnvironmentId): 
            if self.environmentManager.isValidEnvironmentId(self.currentEnvironment.uniqueEnvironmentId):
                self.environmentManager.addEnvironment(self.currentEnvironment)
                self.environmentsComboBox.addItem(self.currentEnvironment.displayName)
            else:
                QMessageBox.warning("Invalid Environment Name", "Please enter a valid environment name.")

        self.environmentManager.save(self.dbManager)

    def setCurrentEnvironment(self, env : Environment):
        self.currentEnvironment = env
        
        self.settingsTable.clear()
        for key, val in env.settings.items():
            self.settingsTable.addEntry([key, val])

    def onAddKeyValue(self):
        if self.currentEnvironment != None:
            if not self.environmentManager.isValidEnvironmentId(self.currentEnvironment.uniqueEnvironmentId):
                QMessageBox.warning(self, "Invalid Environment Name", "Please enter a valid environment name.")
                return

            key = self.widget.keyLineEdit.text()

            if key.strip() == "":
                QMessageBox.warning(self, "Invalid Key", "Please enter a valid key.")
                return

            value = self.widget.valueLineEdit.text()
            if not key in self.currentEnvironment.settings.keys():
                self.settingsTable.addEntry([key, value])
            else:
                for i in range(0, len(self.settingsTable.entries)):
                    existingTableKey = self.settingsTable.entries[i][0]
                    if existingTableKey == key:
                        self.settingsTable.replaceEntryAtRow(i, [key, value])
                        break

            self.currentEnvironment.settings[key] = value
        else:
            QMessageBox.warning(self, "Invalid Environment Name", "Please enter a valid environment name.")

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