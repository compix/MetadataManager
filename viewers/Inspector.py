from qt_extensions.DockWidget import DockWidget
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from MetadataManagerCore.mongodb_manager import MongoDBManager
from viewers.CollectionViewer import CollectionViewer

class Inspector(DockWidget):
    def __init__(self, parentWindow, dbManager : MongoDBManager, collectionViewer: CollectionViewer):
        super().__init__("Inspector", parentWindow, asset_manager.getUIFilePath("inspector.ui"))
        
        self.dbManager = dbManager
        self.collectionViewer = collectionViewer

    def showItem(self, uid):
        form = self.widget.formLayout
        qt_util.clearContainer(form)
        item = self.dbManager.findOneInCollections(uid, self.collectionViewer.getSelectedCollectionNames())
        self.showDictionary(item)

    def showDictionary(self, dataDict: dict):
        form = self.widget.formLayout
        qt_util.clearContainer(form)

        if dataDict != None:
            for key, val in dataDict.items():
                valueEdit = QtWidgets.QLineEdit(self.widget)
                valueEdit.setReadOnly(True)
                valueEdit.setText(str(val) if val else '')
                valueEdit.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")
                form.addRow(str(key), valueEdit)