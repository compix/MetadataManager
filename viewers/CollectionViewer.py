from MetadataManagerCore.mongodb_manager import MongoDBManager
from PySide2 import QtWidgets, QtCore, QtUiTools
from MetadataManagerCore import Keys
from qt_extensions import qt_util
import os
from qt_extensions.DockWidget import DockWidget
from assets import asset_manager

class CollectionViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Collection Viewer", parentWindow, asset_manager.getUIFilePath("collectionManager.ui"))
        self.dbManager = None
        self.collectionCheckBoxMap = dict()

        self.collectionsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.collectionPropertiesVBox.setAlignment(QtCore.Qt.AlignTop)

        self.collectionsComboBox.currentIndexChanged.connect(self.onCollectionsComboBoxIndexChanged)

        self.collectionKeyCheckBoxMap = dict()

    def setDataBaseManager(self, dbManager : MongoDBManager):
        self.dbManager = dbManager

    def connectCollectionSelectionUpdateHandler(self, command):
        for collectionCheckBox in self.collectionCheckBoxMap.values():
            collectionCheckBox.stateChanged.connect(command)

    def onCollectionsComboBoxIndexChanged(self):
        currentCollection = self.collectionsComboBox.currentText()
        keys = self.dbManager.findAllKeysInCollection(currentCollection)
        qt_util.clearContainer(self.widget.collectionPropertiesVBox)
        self.collectionKeyCheckBoxMap.clear()

        _, curKeys = self.dbManager.extractTableHeaderAndDisplayedKeys([currentCollection])

        for key in keys:
            checkbox = QtWidgets.QCheckBox(self.widget)
            checkbox.setText(key)
            self.collectionKeyCheckBoxMap[key] = checkbox

            checkbox.setChecked(key in curKeys)

            checkbox.stateChanged.connect(lambda: self.updateHeader(currentCollection))
            self.widget.collectionPropertiesVBox.addWidget(checkbox)

    def updateHeader(self, collectionName):
        header = []
        for key, value in self.collectionKeyCheckBoxMap.items():
            if value.isChecked():
                header.append([key, key])

        self.dbManager.setTableHeader(collectionName, header)
        
    @property
    def collectionsLayout(self):
        return self.widget.collectionsLayout

    @property
    def collectionsComboBox(self) -> QtWidgets.QComboBox:
        return self.widget.collectionsComboBox

    def updateCollections(self):
        self.collectionCheckBoxMap.clear()
        self.collectionsComboBox.clear()
        qt_util.clearContainer(self.collectionsLayout)
        for collectionName in self.dbManager.getVisibleCollectionNames():
            self.addCollectionCheckbox(collectionName)
            self.collectionsComboBox.addItem(collectionName)

    def addCollectionCheckbox(self, collectionName):
        collectionCheckbox = QtWidgets.QCheckBox(self.widget)
        collectionCheckbox.setText(collectionName)
        self.collectionCheckBoxMap[collectionName] = collectionCheckbox
        self.collectionsLayout.addWidget(collectionCheckbox)

    def getSelectedCollectionNames(self):
        for collectionName in self.dbManager.getVisibleCollectionNames():
            collectionCheckbox = self.collectionCheckBoxMap.get(collectionName)
            if collectionCheckbox != None:
                if collectionCheckbox.isChecked():
                    yield collectionName
            else:
                print(f"Error: Could not find collection checkbox {collectionName}")

    def saveState(self, settings: QtCore.QSettings):
        for collectionName in self.dbManager.getVisibleCollectionNames():
            collectionCheckbox = self.collectionCheckBoxMap.get(collectionName)
            if collectionCheckbox != None:
                settings.setValue(f"{collectionName}CheckboxState", 1 if collectionCheckbox.isChecked() else 0)

    def restoreState(self, settings: QtCore.QSettings):
        for collectionName in self.dbManager.getVisibleCollectionNames():
            collectionCheckbox = self.collectionCheckBoxMap.get(collectionName)
            if collectionCheckbox != None:
                checkState = settings.value(f"{collectionName}CheckboxState")
                if checkState != None:
                    collectionCheckbox.setChecked(int(checkState) == 1)