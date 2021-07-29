from core.Event import Event
from qt_extensions.InspectorWidget import InspectorWidget, InspectorWidgetType
from typing import Any
from MetadataManagerCore.mongodb_manager import MongoDBManager
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QRegExp
from PySide2.QtGui import QRegExpValidator
from PySide2.QtWidgets import QLineEdit, QMessageBox, QFileDialog, QPushButton, QWidget
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.environment.Environment import Environment
from qt_extensions.SimpleTableModel import SimpleTableModel
import json, os
import subprocess
import logging
import re

class EnvironmentViewer(object):
    def __init__(self, parentWidget: QWidget, environmentManager : EnvironmentManager, dbManager : MongoDBManager):
        super().__init__()

        self.widget: QWidget = asset_manager.loadUIFile("environment.ui")
        self.widget.setParent(parentWidget)
        
        self.environmentManager : EnvironmentManager = environmentManager
        self.dbManager : MongoDBManager = dbManager
        self.environment = None

        self.logger = logging.getLogger(__name__)

        self.inspectorWidget = None
        self.widget.addButton.clicked.connect(self.onAddKeyValue)

        self.settingsTableView : QtWidgets.QTableView = self.widget.settingsTableView
        self.settingsTable = SimpleTableModel(self.settingsTableView, ["Key", "Value"])
        self.settingsTableView.setModel(self.settingsTable)

        self.environment = None

        self.widget.chooseFileButton.clicked.connect(self.onChooseFile)
        self.widget.chooseDirButton.clicked.connect(self.onChooseDir)

        self.settingsTableView.doubleClicked.connect(self.onTableViewDoubleClicked)

        self.widget.selectValueFileInExplorerButton.clicked.connect(self.onSelectValueFileInExplorerButton)
        self.widget.deleteEntryButton.clicked.connect(self.onDeleteEntry)

        keyLineEdit: QLineEdit = self.widget.keyLineEdit
        keyLineEdit.textChanged.connect(self.onKeyLineEditTextChanged)
        self.widget.searchButton.clicked.connect(lambda: self.updateSettingsTable())
        
        for v in InspectorWidgetType:
            self.widget.valueTypeComboBox.addItem(v.value)

        self.widget.valueTypeComboBox.currentTextChanged.connect(self.onValueTypeComboBoxSelectionChanged)
        self.onValueTypeComboBoxSelectionChanged()

        self.onNewEnvironmentAdded = Event()
        self.ignoreFilter = None
        self.allowSave = True

    def setKeyDisplayIgnoreFilter(self, filterString: str):
        """If the filter is satisfied the entry won't be displayed in the settings table.
        """
        self.ignoreFilter = filterString

    def setEnvironment(self, environment: Environment):
        self.environment = environment
        self.updateSettingsTable()

    def onKeyLineEditTextChanged(self, key: str):
        searchButton: QPushButton = self.widget.searchButton

        if searchButton.isChecked():
            self.updateSettingsTable()

    def updateSettingsTable(self):
        if not self.environment:
            return

        searchButton: QPushButton = self.widget.searchButton

        self.settingsTable.clear()
        for key, val in self.environment.settings.items():
            if self.ignoreFilter:
                if re.search(self.ignoreFilter, key):
                    continue

            if searchButton.isChecked():
                if re.search(self.widget.keyLineEdit.text(), key) or (isinstance(val, str) and re.search(self.widget.keyLineEdit.text(), val)):
                    self.settingsTable.addEntry([key, val])
            else:
                self.settingsTable.addEntry([key, val])

    def onDeleteEntry(self):
        if self.environment != None:
            key = self.widget.keyLineEdit.text()

            if key in self.environment.settings:
                ret = QMessageBox.question(self.widget, "Delete Entry", "Are you sure you want to delete the settings entry?")
                if ret == QMessageBox.Yes:
                    del self.environment.settings[key]

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
                value = self.environment.evaluateSettingsValue(self.inspectorWidget.value)
                if isinstance(value, str) and os.path.exists(value):
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(value)}"')
            except Exception as e:
                print(e)

    def onValueTypeComboBoxSelectionChanged(self):
        valueType = InspectorWidgetType(self.widget.valueTypeComboBox.currentText())

        self.inspectorWidget = InspectorWidget(editable=True)
        self.inspectorWidget.constructFromInspectorWidgetType(valueType)
        self.onUpdateValueWidget()

    def updateValueWidget(self, value: Any):
        self.inspectorWidget = InspectorWidget(value=value, editable=True)
        self.onUpdateValueWidget()

    def onUpdateValueWidget(self):
        qt_util.clearContainer(self.widget.valueFrame.layout())
        self.widget.valueFrame.layout().addWidget(self.inspectorWidget.widget)
        self.widget.setTabOrder(self.widget.keyLineEdit, self.inspectorWidget.widget)
        self.inspectorWidget.onReturnPressedEvent.subscribe(self.onAddKeyValue)

        valueType = self.inspectorWidget.type
        self.widget.chooseFileButton.setEnabled(valueType == InspectorWidgetType.String)
        self.widget.chooseDirButton.setEnabled(valueType == InspectorWidgetType.String)
        self.widget.selectValueFileInExplorerButton.setEnabled(valueType == InspectorWidgetType.String)

        self.widget.valueTypeComboBox.currentTextChanged.disconnect()
        self.widget.valueTypeComboBox.setCurrentText(valueType.value)
        self.widget.valueTypeComboBox.currentTextChanged.connect(self.onValueTypeComboBoxSelectionChanged)

    def onTableViewDoubleClicked(self, idx):
        entry = self.settingsTable.entries[idx.row()]
        self.widget.keyLineEdit.setText(entry[0])
        self.updateValueWidget(entry[1])

        value = self.environment.evaluateSettingsValue(entry[1])

        self.widget.selectValueFileInExplorerButton.setEnabled(isinstance(value, str) and os.path.exists(value))

        self.widget.deleteEntryButton.setEnabled(True)

    def onChooseFile(self):
        fileName,_ = QFileDialog.getOpenFileName(self, "Open", "", "Any File (*.*)")
        if fileName != None and fileName != "":
            self.inspectorWidget.value = fileName
            self.onAddKeyValue()

    def onChooseDir(self):
        dirName = QFileDialog.getExistingDirectory(self, "Open", "")
        if dirName != None and dirName != "":
            self.inspectorWidget.value = dirName
            self.onAddKeyValue()

    def setupKeyLineEdit(self):
        # Only allow alphabetic chars, digits, _, spaces:
        rx = QRegExp("[A-Za-z0-9 _]+")
        validator = QRegExpValidator(rx, self.widget)
        self.widget.keyLineEdit.setValidator(validator)
        
    def saveEnvironment(self):
        if not self.allowSave:
            return
            
        if self.environment != None and not self.environmentManager.hasEnvironmentId(self.environment.uniqueEnvironmentId): 
            if self.environmentManager.isValidEnvironmentId(self.environment.uniqueEnvironmentId):
                self.environmentManager.addEnvironment(self.environment)
                self.onNewEnvironmentAdded(self.environment)
            else:
                QMessageBox.warning(self.widget, "Invalid Environment Name", "Please enter a valid environment name.")

        self.environmentManager.saveToDatabase()

        if self.environment:
            self.exportSettingsAsJson(self.environment.autoExportPath)

    def validateCurrentEnvironment(self):
        if self.environment == None or not self.environmentManager.isValidEnvironmentId(self.environment.uniqueEnvironmentId):
            QMessageBox.warning(self, "Invalid Environment Name", "Please enter a valid environment name.")
            return False

        return True

    def addEntry(self, key, value, save=True):
        """
        Adds a new entry or replaces an existing value if the key is already present in the settings dictionary.
        """
        if self.validateCurrentEnvironment():
            if key.strip() == "":
                QMessageBox.warning(self.widget, "Invalid Key", "Please enter a valid key.")
                return False
    
            if not key in self.environment.settings.keys():
                self.settingsTable.addEntry([key, value])
            else:
                for i in range(0, len(self.settingsTable.entries)):
                    existingTableKey = self.settingsTable.entries[i][0]
                    if existingTableKey == key:
                        self.settingsTable.replaceEntryAtRow(i, [key, value])
                        break

            self.widget.deleteEntryButton.setEnabled(True)
            self.environment.settings[key] = value
            if save:
                self.saveEnvironment()
            return True
        else:
            return False

    def onAddKeyValue(self):
        key = self.widget.keyLineEdit.text()
        try:
            value = self.inspectorWidget.value if self.inspectorWidget else ''
        except Exception as e:
            QMessageBox.warning(self.widget, "Failed Adding Value", f"An error occurred: {str(e)}")
            return

        self.addEntry(key, value)

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
    
    def openImportFromSettingsFileDialog(self):
        if not self.validateCurrentEnvironment():
            return

        filePath,_ = QFileDialog.getOpenFileName(self.widget, "Open Settings File", "", "Any File (*.*)")

        if filePath != None and filePath != "":
            # Try to open a json settings file first
            readFromJson = False

            try:
                with open(filePath) as f:
                    settingsDict = json.load(f)

                    for key,value in settingsDict.items():
                        self.addEntry(key, value)

                readFromJson = True
            except:
                pass

            # If json settings file could not be opened read a settings file defined with key=value line by line
            if not readFromJson:
                with open(filePath, 'r') as f:
                    for line in f:
                        tokens = line.split("=")
                        
                        if len(tokens) == 2:
                            key = tokens[0].strip()
                            value = tokens[1].strip()

                            self.addEntry(key, value, save=False)

            self.saveEnvironment()

    def exportSettingsAsJson(self, filePath):
        if filePath != None and filePath != "":
            try:
                with open(filePath, 'w+') as f:
                    json.dump(self.environment.getEvaluatedSettings(), f, indent=4, sort_keys=True)
            except Exception as e:
                self.logger.error(f'Failed to export settings file at path {filePath}. Exception: {str(e)}')

    def openExportAsJsonFileDialog(self):
        if not self.validateCurrentEnvironment():
            return

        filePath,_ = QFileDialog.getSaveFileName(self.widget, "Save Settings As Json", "", "Any File (*.*)")
        self.exportSettingsAsJson(filePath)

    def openSelectAutoExportPathFileDialog(self):
        if not self.environment:
            QMessageBox.warning(self.widget, "No Active Environment", "Please set an active environment.")
            return

        filePath,_ = QFileDialog.getSaveFileName(self.widget, "Save Settings As Json", "", "Any File (*.*)")

        if filePath != None and filePath != "":
            self.environment.autoExportPath = filePath
            self.exportSettingsAsJson(filePath)
            self.saveEnvironment()

    def saveState(self, settings: QtCore.QSettings):
        pass

    def restoreState(self, settings: QtCore.QSettings):
        pass