# This Python file uses the following encoding: utf-8
import sys
from PySide2 import QtCore, QtWidgets
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide2.QtCore import QFile, QObject, QEvent
import qdarkstyle
from enum import Enum
from mongodb_manager import MongoDBManager
import operator

g_company = "WK"
g_appName = "Metadata-Manager"
g_mongodbHost = "mongodb://localhost:27017/"
g_databaseName = "centralRepository"

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("Metadata Manager")

def on_button_click():
    ret = QMessageBox.warning(window, "TestDialog",
                              "The document has been modified.\n" + \
                              "Do you want to save your changes?",
                              QMessageBox.Save | QMessageBox.Ok | QMessageBox.Cancel,
                              QMessageBox.Save)

class Style(Enum):
    Dark = 0
    Light = 1

class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent, entries, header, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.entries = entries
        self.header = header

    def rowCount(self, parent):
        return len(self.entries)

    def columnCount(self, parent):
        return len(self.entries[0])

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        return self.entries[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        # Sort table by given column number col
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries = sorted(self.entries, key=operator.itemgetter(col))
        if order == QtCore.Qt.DescendingOrder:
            self.entries.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntry(self, entry):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.append(entry)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def addEntries(self, entries):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.entries.extend(entries)
        self.emit(QtCore.SIGNAL("layoutChanged()"))

class MainWindowManager(QObject):
    def __init__(self, app):
        super(MainWindowManager, self).__init__()
        self.app = app
        self.currentStyle = None

        file = QFile("./main.ui")
        file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(file)

        self.window.installEventFilter(self)

        self.window.menuView.addAction(self.window.previewDockWidget.toggleViewAction())
        self.window.menuView.addAction(self.window.inspectorDockWidget.toggleViewAction())
        self.window.menuView.addAction(self.window.actionsDockWidget.toggleViewAction())
        self.window.menuView.addAction(self.window.commentsDockWidget.toggleViewAction())

        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

        self.dbManager = MongoDBManager(g_mongodbHost, g_databaseName)
        self.dbManager.insertExampleEntries()

        self.window.collectionsVLayout.setAlignment(QtCore.Qt.AlignTop)

        self.updateCollections()

        self.restoreState()

        self.tableModel = TableModel(self.window, [], ["Name","Address"])
        self.window.tableView.setModel(self.tableModel)
        self.viewItems()

    def updateCollections(self):
        self.clearContainer(self.window.collectionsVLayout)
        for collectionName in self.dbManager.getCollectionNames():
            collectionCheckbox = QtWidgets.QCheckBox(self.window)
            collectionCheckbox.setText(collectionName)
            self.setCollectionCheckbox(collectionName, collectionCheckbox)
            self.window.collectionsVLayout.addWidget(collectionCheckbox)

    # Container/Layout
    def clearContainer(self, container):
        for i in reversed(range(container.count())): 
            container.itemAt(i).widget().setParent(None)

    def setCollectionCheckbox(self, collectionName, collectionCheckbox):
        setattr(self.window, collectionName, collectionCheckbox)

    def getCollectionCheckbox(self, collectionName):
        return getattr(self.window, collectionName, None)

    def getSelectedCollectionNames(self):
        for collectionName in self.dbManager.getCollectionNames():
            if self.getCollectionCheckbox(collectionName).isChecked():
                yield collectionName

    def filteredItems(self, collection):
        return collection.find({}, {'_id': False})

    # TODO: Find the header for table by getting all unique displayed entries from all items.
    #       If a key is missing in a given item/document -> 'None' is displayed.
    def viewItems(self):
        for collectionName in self.getSelectedCollectionNames():
            for item in self.filteredItems(self.dbManager.db[collectionName]):
                self.tableModel.addEntry([item["name"], item["address"]])

    def setStyle(self, style):
        if (style == Style.Dark or style == None) and self.currentStyle != style:
            self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
        elif style == Style.Light and self.currentStyle != style:
            self.app.setStyleSheet(None)
        
        self.window.actionDark.setChecked(style == Style.Dark)
        self.window.actionLight.setChecked(style == Style.Light)
        self.currentStyle = style

    def saveState(self):
        settings = QtCore.QSettings(g_company, g_appName)
        settings.setValue("geometry", self.window.saveGeometry())
        settings.setValue("windowState", self.window.saveState())
        settings.setValue("style", self.currentStyle)

        for collectionName in self.dbManager.getCollectionNames():
            if self.getCollectionCheckbox(collectionName) != None:
                settings.setValue(collectionName + "CheckboxState", 1 if self.getCollectionCheckbox(collectionName).isChecked() else 0)

    def restoreState(self):
        settings = QtCore.QSettings(g_company, g_appName)
        self.window.restoreGeometry(settings.value("geometry"))
        self.window.restoreState(settings.value("windowState"))
        self.setStyle(settings.value("style"))

        for collectionName in self.dbManager.getCollectionNames():
            if self.getCollectionCheckbox(collectionName) != None:
                checkState = settings.value(collectionName + "CheckboxState")
                if checkState != None:
                    self.getCollectionCheckbox(collectionName).setChecked(checkState)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Close:
            self.quitApp()
            event.ignore()
            return True
        return super(MainWindowManager, self).eventFilter(obj, event)

    @QtCore.Slot()
    def quitApp(self):
        self.saveState()
        self.window.removeEventFilter(self)
        app.quit()

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication([])
    w = MainWindowManager(app)
    w.show()
    sys.exit(app.exec_())
