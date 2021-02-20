from MetadataManagerCore.mongodb_manager import MongoDBManager, CollectionHeaderKeyInfo
from PySide2 import QtWidgets, QtCore, QtUiTools
from PySide2.QtWidgets import QTableWidget, QTableWidgetItem, QLineEdit
from MetadataManagerCore import Keys
from qt_extensions import qt_util
import os
from qt_extensions.DockWidget import DockWidget
import asset_manager
from MetadataManagerCore.Event import Event

class CollectionViewer(DockWidget):
    def __init__(self, parentWindow, dbManager : MongoDBManager):
        super().__init__("Collection Viewer", parentWindow, asset_manager.getUIFilePath("collectionManager.ui"))
        self.dbManager = dbManager
        self.collectionCheckBoxMap = dict()

        self.collectionsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.collectionPropertiesVBox.setAlignment(QtCore.Qt.AlignTop)

        self.collectionsComboBox.currentIndexChanged.connect(self.onCollectionsComboBoxIndexChanged)

        self.collectionHeaderKeyInfos = []

        self.collectionTableWidget : QTableWidget = self.widget.collectionPropertiesTableWidget
        self.updateCollections()

        self.headerUpdatedEvent = Event()

        self.widget.refreshCollectionsButton.clicked.connect(self.onRefreshCollections)

        self.settings = None
        self.collectionCheckboxChangeListeners = []

    def onRefreshCollections(self):
        self.updateCollections()
        self.collectionsComboBox.setCurrentIndex(0)

        if self.settings:
            self.restoreState(self.settings)

        self.onCollectionCheckBoxStateChanged()

    def connectCollectionSelectionUpdateHandler(self, command):
        self.collectionCheckboxChangeListeners.append(command)

    def onCollectionCheckBoxStateChanged(self):
        if self.settings:
            self.saveState(self.settings)

        for func in self.collectionCheckboxChangeListeners:
            func()

    def onCollectionsComboBoxIndexChanged(self):
        currentCollection = self.collectionsComboBox.currentText()
        if not currentCollection:
            return

        keys = self.dbManager.findAllKeysInCollection(currentCollection)
        self.collectionTableWidget.clear()
        self.collectionHeaderKeyInfos.clear()

        self.collectionTableWidget.setColumnCount(3)
        self.collectionTableWidget.setHorizontalHeaderItem(0, QTableWidgetItem("Key"))
        self.collectionTableWidget.setHorizontalHeaderItem(1, QTableWidgetItem("Shown"))
        self.collectionTableWidget.setHorizontalHeaderItem(2, QTableWidgetItem("Display Name"))
        self.collectionTableWidget.setRowCount(len(keys))

        headerInfos = self.dbManager.extractCollectionHeaderInfo([currentCollection])
        headerKeyToInfo = {i.key:i for i in headerInfos}
        self.dbManager.collectionsMD.up

        rowIdx = 0
        for key in keys:
            checkbox = QtWidgets.QCheckBox(self.widget)
            checkbox.setText("")

            headerInfo = headerKeyToInfo.get(key)
            if not headerInfo:
                headerInfo = CollectionHeaderKeyInfo(key, key, True)

            checkbox.setChecked(headerInfo.displayed)

            checkbox.stateChanged.connect(lambda: self.updateHeader(currentCollection))

            self.collectionTableWidget.setItem(rowIdx, 0, QTableWidgetItem(key))
            self.collectionTableWidget.setCellWidget(rowIdx, 1, checkbox)
            edit = QLineEdit()
            edit.setText(headerInfo.displayName)
            edit.textChanged.connect(lambda txt: self.updateHeader(currentCollection))
            self.collectionTableWidget.setCellWidget(rowIdx, 2, edit)

            headerInfo.displayCheckbox = checkbox
            headerInfo.displayNameEdit = edit
            self.collectionHeaderKeyInfos.append(headerInfo)

            rowIdx += 1

        if not headerInfos or len(headerInfos) == 0:
            self.updateHeader(currentCollection)

    def updateHeader(self, collectionName):
        for headerKeyInfo in self.collectionHeaderKeyInfos:
            headerKeyInfo.displayed = headerKeyInfo.displayCheckbox.isChecked()
            headerKeyInfo.displayName = headerKeyInfo.displayNameEdit.text()

        self.dbManager.setCollectionHeaderInfo(collectionName, self.collectionHeaderKeyInfos)

        self.headerUpdatedEvent()
        
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
        collectionCheckbox.stateChanged.connect(self.onCollectionCheckBoxStateChanged)

    def yieldSelectedCollectionNames(self):
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
        self.settings = settings
        for collectionName in self.dbManager.getVisibleCollectionNames():
            collectionCheckbox = self.collectionCheckBoxMap.get(collectionName)
            if collectionCheckbox != None:
                checkState = settings.value(f"{collectionName}CheckboxState")
                if checkState != None:
                    collectionCheckbox.setChecked(int(checkState) == 1)