from qt_extensions.DockWidget import DockWidget
from assets import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets

class Inspector(DockWidget):
    def __init__(self, parentWindow, dbManager):
        super().__init__("Inspector", parentWindow, asset_manager.getUIFilePath("inspector.ui"))
        
        self.dbManager = dbManager
        
    def showItem(self, uid):
        form = self.widget.formLayout
        qt_util.clearContainer(form)
        item = self.dbManager.findOne(uid)
        if item != None:
            for key, val in item.items():
                form.addRow(str(key), QtWidgets.QLabel(str(val)))