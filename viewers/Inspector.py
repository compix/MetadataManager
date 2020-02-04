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
                valueLabel = QtWidgets.QLabel(str(val))
                valueLabel.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard | Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)

                form.addRow(str(key), valueLabel)