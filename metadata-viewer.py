# This Python file uses the following encoding: utf-8
import sys
from PySide2 import QtCore, QtWidgets
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide2.QtCore import QFile, QObject, QEvent, Qt
from PySide2.QtCore import QThreadPool, QRunnable
import qdarkstyle
from enum import Enum
from mongodb_manager import MongoDBManager
import operator
from MetadataManagerCore.util import timeit
from multiprocessing.dummy import Pool as ThreadPool 
from time import sleep
import qt_util
import json
import numpy as np

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

class LambdaTask(QRunnable):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        QRunnable.__init__(self)

    def run(self):
        self.func(*self.args, **self.kwargs)

class Completer(QtWidgets.QCompleter):
    def splitPath(self, path):
        return path.split(' ')

    def pathFromIndex(self, index):
        result = []
        while index.isValid():
            result = [self.model().data(index, QtCore.Qt.DisplayRole)] + result
            index = index.parent()
        r = ' '.join(result)
        return r

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

    """
    The heaeder won't be updated if the current header is equal to the new given header (order and value comparison).
    Note: Upadting the header removes all entries.
    """
    def updateHeader(self, header, displayedKeys):
        if self.header != header:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.displayedKeys = displayedKeys
            self.entries = []
            self.header = header
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def clear(self):
        if len(self.entries) > 0:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.entries = []
            self.emit(QtCore.SIGNAL("layoutChanged()"))

class MainWindowManager(QObject):
    def __init__(self, app):
        super(MainWindowManager, self).__init__()
        self.app = app
        self.currentStyle = None
        self.applicationQuitting = False

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
        self.mainProgressBar = QtWidgets.QProgressBar(self.window)
        self.window.statusBar().addWidget(self.mainProgressBar)

        self.itemCountLabel = QtWidgets.QLabel(self.window)
        self.window.statusBar().addWidget(self.itemCountLabel)
        self.updateCollections()

        self.restoreState()

        header, displayedKeys = self.extractTableHeaderAndDisplayedKeys()
        self.tableModel = TableModel(self.window, [], header, displayedKeys)
        self.window.tableView.setModel(self.tableModel)

        self.window.findPushButton.clicked.connect(lambda:QThreadPool.globalInstance().start(LambdaTask(self.viewItems)))

        self.setupFilter()

    def setupFilter(self):
        wordList = [("\"" + f + "\"") for f in self.tableModel.displayedKeys]
        filterCompleter = Completer(wordList, self)
        filterCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        filterCompleter.setFilterMode(Qt.MatchContains)
        filterCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.window.filterEdit.setCompleter(filterCompleter)

        wordList = [f for f in self.tableModel.displayedKeys]
        distinctCompleter = Completer(wordList, self)
        distinctCompleter.setCaseSensitivity(Qt.CaseInsensitive)
        distinctCompleter.setFilterMode(Qt.MatchContains)
        distinctCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.window.distinctEdit.setCompleter(distinctCompleter)
    
    def insertCompletion(self, completionText):
        print(completionText)

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

    def getItemsFilter(self):
        try:
            filterText = self.window.filterEdit.text()
            if len(self.window.filterEdit.text()) == 0:
                return {}
            
            filter = json.loads(filterText)
            return filter
        except:    
            return {"_id":"None"}

    def filteredItems(self, collection):
        filtered = collection.find(self.getItemsFilter(), {'_id': False})
        distinctKey = self.window.distinctEdit.text()
        
        if len(distinctKey) > 0:
            distinctKeys = filtered.distinct(distinctKey)
            distinctMap = dict(zip(distinctKeys, np.repeat(False, len(distinctKeys))))
            for item in filtered:
                val = item.get(distinctKey)
                if val != None:
                    if not distinctMap.get(val):
                        distinctMap[val] = True
                        yield item
        else:
            for item in filtered:
                yield item

    def getMaxDisplayedTableItems(self):
        num = 0
        filter = self.getItemsFilter()
        distinctKey = self.window.distinctEdit.text()

        for collectionName in self.getSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            if len(distinctKey) > 0:
                num += len(collection.find(self.getItemsFilter()).distinct(distinctKey))
            else:
                num += collection.count_documents(filter)

        return num

    @timeit
    def viewItems(self):
        if len(self.tableModel.displayedKeys) == 0:
            return

        qt_util.runInMainThread(self.tableModel.clear)
        maxDisplayedItems = self.getMaxDisplayedTableItems()
        qt_util.runInMainThread(lambda:self.itemCountLabel.setText("Item Count: " + str(maxDisplayedItems)))

        if maxDisplayedItems == 0:
            return
        qt_util.runInMainThread(self.mainProgressBar.setMaximum, maxDisplayedItems)

        entries = []
        i = 0
        for collectionName in self.getSelectedCollectionNames():
            for item in self.filteredItems(self.dbManager.db[collectionName]):
                if self.applicationQuitting:
                    return

                i += 1
                tableEntry = self.extractTableEntry(self.tableModel.displayedKeys, item)
                entries.append(tableEntry)
                qt_util.runInMainThread(self.mainProgressBar.setValue, i)
        
        qt_util.runInMainThread(self.tableModel.addEntries, entries)

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
        self.applicationQuitting = True
        QThreadPool.globalInstance().waitForDone()
        app.quit()

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QApplication([])
    w = MainWindowManager(app)
    w.show()
    sys.exit(app.exec_())
