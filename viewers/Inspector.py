from qt_extensions.DockWidget import DockWidget
from assets import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt

class Inspector(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Inspector", parentWindow, asset_manager.getUIFilePath("inspector.ui"))
        
        self.dbManager = None

    def setDatabaseManager(self, dbManager):
        self.dbManager = dbManager
        
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