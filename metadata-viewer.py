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
from MetadataManagerCore.util import timeit

g_company = "WK"
g_appName = "Metadata-Manager"
g_mongodbHost = "mongodb://localhost:27017/"
g_databaseName = "centralRepository"
g_collectionsMD = "collectionsMD"
g_usersCollection = "users"
g_hiddenCollections = set([g_collectionsMD])

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
    def __init__(self, parent, entries, header, displayedKeys, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.entries = entries
        self.header = header
        self.displayedKeys = displayedKeys

    def rowCount(self, parent):
        return len(self.entries)

    def columnCount(self, parent):
        return len(self.entries[0]) if len(self.entries) > 0 else 0 

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

    def updateHeader(self, header, displayedKeys):
        if self.header != header:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.displayedKeys = displayedKeys
            self.entries = []
            self.header = header
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
        #for i in range(0,10000):
        #    self.dbManager.insertExampleEntries()

        self.window.collectionsVLayout.setAlignment(QtCore.Qt.AlignTop)

        self.dbManager.db[g_collectionsMD].delete_one({"_id":"test"})
        self.dbManager.insertOne(g_collectionsMD, {"_id": "test", "tableHeader":[["Name", "name"], ["Address", "address"], ["Test", "test"]]})
        #self.dbManager.db[g_collectionsMD].update_one({"_id": "test"}, {"$set": {"displayedTableKeys":["name", "address"]}})
        #self.window.statusBar().showMessage("test")
        self.updateCollections()

        self.restoreState()

        header, displayedKeys = self.extractTableHeaderAndDisplayedKeys()
        self.tableModel = TableModel(self.window, [], header, displayedKeys)
        self.window.tableView.setModel(self.tableModel)
        self.viewItems()

    def updateCollections(self):
        self.clearContainer(self.window.collectionsVLayout)
        for collectionName in self.getAvailableCollectionNames():
            collectionCheckbox = QtWidgets.QCheckBox(self.window)
            collectionCheckbox.setText(collectionName)
            self.setCollectionCheckbox(collectionName, collectionCheckbox)
            self.window.collectionsVLayout.addWidget(collectionCheckbox)

    def getAvailableCollectionNames(self):
        for cn in self.dbManager.getCollectionNames():
            if not cn in g_hiddenCollections:
                yield cn

    # Container/Layout
    def clearContainer(self, container):
        for i in reversed(range(container.count())): 
            container.itemAt(i).widget().setParent(None)

    def setCollectionCheckbox(self, collectionName, collectionCheckbox):
        setattr(self.window, collectionName, collectionCheckbox)

    def getCollectionCheckbox(self, collectionName):
        return getattr(self.window, collectionName, None)

    def getSelectedCollectionNames(self):
        for collectionName in self.getAvailableCollectionNames():
            if self.getCollectionCheckbox(collectionName).isChecked():
                yield collectionName

    def filteredItems(self, collection):
        return collection.find({}, {'_id': False})

    # TODO: Find the header for table by getting all unique displayed entries from all items.
    #       If a key is missing in a given item/document -> 'None' is displayed.
    @timeit
    def viewItems(self):
        if len(self.tableModel.displayedKeys) == 0:
            return

        for collectionName in self.getSelectedCollectionNames():
            for item in self.filteredItems(self.dbManager.db[collectionName]):
                self.tableModel.addEntry(self.extractTableEntry(self.tableModel.displayedKeys, item))

    # item: mongodb document
    def extractTableEntry(self, displayedKeys, item):
        assert(len(displayedKeys) > 0)
        entry = []
        for e in displayedKeys:
            val = item.get(e)
            entry.append(val if val != None else "N.D.")

        return entry

    def extractTableHeaderAndDisplayedKeys(self):
        header = []
        keys = []
        # Go through the selected collection metadata, check displayed table info
        # and add unique entries:
        collectionsMD = self.dbManager.db[g_collectionsMD]
        for collectionName in self.getSelectedCollectionNames():
            cMD = collectionsMD.find_one({"_id":collectionName})
            if cMD:
                cTableHeader = cMD["tableHeader"]
                if cTableHeader != None:
                    assert(len(e) == 2 for e in cTableHeader)
                    header = header + [e[0] for e in cTableHeader if e[1] not in keys]
                    keys = keys + [e[1] for e in cTableHeader if e[1] not in keys]

        return header, keys

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

        for collectionName in self.getAvailableCollectionNames():
            if self.getCollectionCheckbox(collectionName) != None:
                settings.setValue(collectionName + "CheckboxState", 1 if self.getCollectionCheckbox(collectionName).isChecked() else 0)

    def restoreState(self):
        settings = QtCore.QSettings(g_company, g_appName)
        self.window.restoreGeometry(settings.value("geometry"))
        self.window.restoreState(settings.value("windowState"))
        self.setStyle(settings.value("style"))

        for collectionName in self.getAvailableCollectionNames():
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
