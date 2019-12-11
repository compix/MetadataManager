from MetadataManagerCore.mongodb_manager import MongoDBManager
from PySide2 import QtWidgets, QtCore, QtUiTools
from MetadataManagerCore import Keys
import qt_extentions
import os

class CollectionViewer(object):
    def __init__(self, window, dbManager : MongoDBManager):
        self.dbManager = dbManager
        self.window = window
        self.collectionCheckBoxMap = dict()

        uiFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "collectionManager.ui")
        uiFile = QtCore.QFile(uiFilePath)
        uiFile.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.frame = loader.load(uiFile)

        self.collectionsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.frame.collectionPropertiesVBox.setAlignment(QtCore.Qt.AlignTop)
        self.setupDockWidget(window)

        self.collectionsComboBox.currentIndexChanged.connect(self.onCollectionsComboBoxIndexChanged)

        self.collectionKeyCheckBoxMap = dict()

    def connectCollectionSelectionUpdateHandler(self, command):
        for collectionCheckBox in self.collectionCheckBoxMap.values():
            collectionCheckBox.stateChanged.connect(command)

    def setupDockWidget(self, parent):
        self.dockWidget = QtWidgets.QDockWidget("Collection Viewer", parent)
        self.dockWidget.setWidget(self.frame)
        self.dockWidget.setObjectName("collectionViewerDockWidget")

    def onCollectionsComboBoxIndexChanged(self):
        currentCollection = self.collectionsComboBox.currentText()
        keys = self.dbManager.findAllKeysInCollection(currentCollection)
        qt_extentions.clearContainer(self.frame.collectionPropertiesVBox)
        self.collectionKeyCheckBoxMap.clear()

        _, curKeys = self.dbManager.extractTableHeaderAndDisplayedKeys([currentCollection])

        for key in keys:
            checkbox = QtWidgets.QCheckBox(self.window)
            checkbox.setText(key)
            self.collectionKeyCheckBoxMap[key] = checkbox

            checkbox.setChecked(key in curKeys)

            checkbox.stateChanged.connect(lambda: self.updateHeader(currentCollection))
            self.frame.collectionPropertiesVBox.addWidget(checkbox)

    def updateHeader(self, collectionName):
        header = []
        for key, value in self.collectionKeyCheckBoxMap.items():
            if value.isChecked():
                header.append([key, key])

        self.dbManager.setTableHeader(collectionName, header)
        
    @property
    def collectionsLayout(self):
        return self.frame.collectionsLayout

    @property
    def collectionsComboBox(self) -> QtWidgets.QComboBox:
        return self.frame.collectionsComboBox

    def updateCollections(self):
        self.collectionCheckBoxMap.clear()
        self.collectionsComboBox.clear()
        qt_extentions.clearContainer(self.collectionsLayout)
        for collectionName in self.dbManager.getVisibleCollectionNames():
            self.addCollectionCheckbox(collectionName)
            self.collectionsComboBox.addItem(collectionName)

    def addCollectionCheckbox(self, collectionName):
        collectionCheckbox = QtWidgets.QCheckBox(self.window)
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
                    collectionCheckbox.setChecked(checkState)