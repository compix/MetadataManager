# This Python file uses the following encoding: utf-8
import sys
from PySide2 import QtCore, QtWidgets, QtUiTools, QtGui
import qdarkstyle
from enum import Enum
from MetadataManagerCore.mongodb_manager import MongoDBManager
import operator
from MetadataManagerCore.util import timeit
from multiprocessing.dummy import Pool as ThreadPool 
from time import sleep
import qt_util
import json
import numpy as np
from qt_extentions import PhotoViewer
import pymongo
from TableModel import TableModel
from qt_extentions import Completer
from MetadataManagerCore import Keys
from VisualScripting.VisualScripting import VisualScripting
from VisualScripting import NodeGraphQt
from PySide2.QtCore import QFile, QTextStream
import qt_extentions
from CollectionViewer import CollectionViewer

company = "WK"
appName = "Metadata-Manager"
mongodbHost = "mongodb://localhost:27017/"
databaseName = "centralRepository"

class Style(Enum):
    Dark = 0
    Light = 1

def constructTestCollection(dbManager : MongoDBManager):
    dbManager.db.drop_collection("Test_Collection")

    names = ["John", "Kevin", "Peter", "Klaus", "Leo"]
    for i in range(0,5):
        dbManager.insertOne("Test_Collection", { "name": names[i%len(names)], "address": f"Highway {i}" })

class MainWindowManager(QtCore.QObject):
    def __init__(self, app):
        super(MainWindowManager, self).__init__()
        self.app = app
        self.currentStyle = None
        self.applicationQuitting = False
        self.documentMoficiations = []

        file = QtCore.QFile("./main.ui")
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.window.installEventFilter(self)

        self.visualScripting = VisualScripting("VisualScripting_SaveData", parentWindow=self.window)

        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

        self.dbManager = MongoDBManager(mongodbHost, databaseName)

        constructTestCollection(self.dbManager)

        settingsUIFile = QtCore.QFile("./settings.ui")
        settingsUIFile.open(QtCore.QFile.ReadOnly)
        self.settingsWindow = loader.load(settingsUIFile)
        self.settingsWindow.setParent(self.window)

        #self.dbManager.db[Keys.collectionsMD].delete_one({"_id":"test"})
        #self.dbManager.insertOne(Keys.collectionsMD, {"_id": "test", "tableHeader":[["Name", "name"], ["Address", "address"], ["Test", "test"]]})
        #self.dbManager.db[collectionsMD].update_one({"_id": "test"}, {"$set": {"displayedTableKeys":["name", "address"]}})
        self.mainProgressBar = QtWidgets.QProgressBar(self.window)
        self.mainProgressBar.setMaximumWidth(100)
        self.mainProgressBar.setMaximumHeight(15)
        self.window.statusBar().addPermanentWidget(self.mainProgressBar)

        self.window.statusBar().showMessage("Test")

        self.collectionViewer = CollectionViewer(self.window, self.dbManager)
        self.collectionViewer.updateCollections()

        self.setupDockWidgets()

        #self.window.findPushButton.clicked.connect(lambda:QThreadPool.globalInstance().start(LambdaTask(self.viewItems)))
        self.window.findPushButton.clicked.connect(self.viewItems)

        self.window.preview = PhotoViewer(self.window)
        self.window.preview.toggleDragMode()
        self.window.previewFrame.layout().addWidget(self.window.preview)

        self.restoreState()

        header, displayedKeys = self.dbManager.extractTableHeaderAndDisplayedKeys(self.collectionViewer.getSelectedCollectionNames())
        self.tableModel = TableModel(self.window, [], header, displayedKeys)
        self.window.tableView.setModel(self.tableModel)

        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.updateTableModelHeader)

        self.setupFilter()

        selModel = self.window.tableView.selectionModel()
        selModel.selectionChanged.connect(self.onTableSelectionChanged)

    def updateTableModelHeader(self):
        header, displayedKeys = self.dbManager.extractTableHeaderAndDisplayedKeys(self.collectionViewer.getSelectedCollectionNames())
        self.tableModel.updateHeader(header, displayedKeys)

    def applyAllDocumentModifications(self):
        if len(self.documentMoficiations) > 0:
            self.initProgress(len(self.documentMoficiations))
            progressCounter = 0
            self.updateProgress(progressCounter)

            for i in reversed(range(len(self.documentMoficiations))):
                progressCounter += 1
                self.documentMoficiations[i].applyModification()
                self.documentMoficiations.pop()
                self.updateProgress(progressCounter)

    def setupDockWidgets(self):
        self.setupDockWidget(self.window.previewDockWidget)
        self.setupDockWidget(self.window.inspectorDockWidget)
        self.setupDockWidget(self.window.actionsDockWidget)
        self.setupDockWidget(self.collectionViewer.dockWidget)
        self.setupDockWidget(self.window.commentsDockWidget)
        self.setupDockWidget(self.settingsWindow)
        self.setupDockWidget(self.visualScripting.getAsDockWidget(self.window))

    def setupDockWidget(self, dockWidget):
        # Add visibility checkbox to view main menu:
        self.window.menuView.addAction(dockWidget.toggleViewAction())
        # Allow window functionality (e.g. maximize)
        dockWidget.topLevelChanged.connect(self.dockWidgetTopLevelChanged)
        self.setDockWidgetFlags(dockWidget)

    def dockWidgetTopLevelChanged(self, changed):
        self.setDockWidgetFlags(self.sender())

    def setDockWidgetFlags(self, dockWidget):
        if dockWidget.isFloating():
            dockWidget.setWindowFlags(QtCore.Qt.CustomizeWindowHint |
                QtCore.Qt.Window | QtCore.Qt.WindowMinimizeButtonHint |
                QtCore.Qt.WindowMaximizeButtonHint |
                QtCore.Qt.WindowCloseButtonHint)
            dockWidget.show()

    def onTableSelectionChanged(self, newSelection, oldSelection):
        for sel in newSelection:
            for idx in sel.indexes():
                uid = self.tableModel.getUID(idx.row())
                item = self.dbManager.findOne(uid)
                if item != None:
                    self.showPreview(item.get("preview"))
                    self.showItemInInspector(uid)

    def addPreviewToAllEntries(self):
        for collectionName in self.collectionViewer.getSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            for item in collection.find({}):
                collection.update_one({"_id":item["_id"]}, {"$set": {"preview":"C:/Users/compix/Desktop/surprised_pikachu.png"}})

    def showPreview(self, path):
        if path == None:
            return

        scene = QtWidgets.QGraphicsScene()
        pixmap = QtGui.QPixmap(path)
        scene.addPixmap(pixmap)
        #self.window.preview.setScene(scene)
        self.window.preview.setPhoto(pixmap)
        #self.window.preview.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def setupFilter(self):
        wordList = [("\"" + f + "\"") for f in self.tableModel.displayedKeys]
        filterCompleter = Completer(wordList, self)
        filterCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filterCompleter.setFilterMode(QtCore.Qt.MatchContains)
        filterCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.window.filterEdit.setCompleter(filterCompleter)

        wordList = [f for f in self.tableModel.displayedKeys]
        distinctCompleter = Completer(wordList, self)
        distinctCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        distinctCompleter.setFilterMode(QtCore.Qt.MatchContains)
        distinctCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.window.distinctEdit.setCompleter(distinctCompleter)

    def showItemInInspector(self, uid):
        form = self.window.inspectorFormLayout
        qt_extentions.clearContainer(form)
        item = self.dbManager.findOne(uid)
        if item != None:
            for key, val in item.items():
                form.addRow(self.window.tr(str(key)), QtWidgets.QLabel(str(val)))

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
        filtered = collection.find(self.getItemsFilter()) # '_id': False
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

        for collectionName in self.collectionViewer.getSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            if len(distinctKey) > 0:
                num += len(collection.find(self.getItemsFilter()).distinct(distinctKey))
            else:
                num += collection.count_documents(filter)

        return num

    def initProgress(self, maxVal):
        qt_util.runInMainThread(self.mainProgressBar.setMaximum, maxVal)

    def updateProgress(self, val):
        qt_util.runInMainThread(self.mainProgressBar.setValue, val)

    @timeit
    def viewItems(self):
        if len(self.tableModel.displayedKeys) == 0:
            return

        qt_util.runInMainThread(self.tableModel.clear)
        maxDisplayedItems = self.getMaxDisplayedTableItems()
        qt_util.runInMainThread(lambda:self.window.itemCountLabel.setText("Item Count: " + str(maxDisplayedItems)))

        if maxDisplayedItems == 0:
            return

        self.initProgress(maxDisplayedItems)

        entries = []
        i = 0
        for collectionName in self.collectionViewer.getSelectedCollectionNames():
            for item in self.filteredItems(self.dbManager.db[collectionName]):
                if self.applicationQuitting:
                    return

                i += 1
                tableEntry = self.extractTableEntry(self.tableModel.displayedKeys, item)
                entries.append(tableEntry)
                self.updateProgress(i)
        
        qt_util.runInMainThread(self.tableModel.addEntries, entries)

    def extractSystemValues(self, item):
        vals = []
        for sysKey in Keys.systemKeys:
            val = item.get(sysKey)
            vals.append(val if val != None else Keys.notDefinedValue)
        
        return vals

    # item: mongodb document
    def extractTableEntry(self, displayedKeys, item):
        assert(len(displayedKeys) > 0)
        entry = [item['_id']]
        for e in displayedKeys:
            val = item.get(e)
            entry.append(val if val != None else Keys.notDefinedValue)

        return entry

    def setStyle(self, style):
        self.app.setStyleSheet(None)
        self.app.setStyle("Fusion")

        if (style == Style.Dark or style == None) and self.currentStyle != style:
            self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
        elif style == Style.Light and self.currentStyle != style:
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
            palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
            palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
            palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
            palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
            self.app.setPalette(palette)

        self.window.actionDark.setChecked(style == Style.Dark)
        self.window.actionLight.setChecked(style == Style.Light)
        self.currentStyle = style

    def saveState(self):
        settings = QtCore.QSettings(company, appName)
        settings.setValue("geometry", self.window.saveGeometry())
        settings.setValue("windowState", self.window.saveState())
        settings.setValue("style", self.currentStyle)
        self.visualScripting.saveWindowState(settings)
        self.collectionViewer.saveState(settings)

    def restoreState(self):
        settings = QtCore.QSettings(company, appName)
        self.window.restoreGeometry(settings.value("geometry"))
        self.window.restoreState(settings.value("windowState"))
        self.setStyle(settings.value("style"))
        self.visualScripting.restoreWindowState(settings)
        self.collectionViewer.restoreState(settings)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QtCore.QEvent.Close:
            self.quitApp()
            event.ignore()
            return True
        return super(MainWindowManager, self).eventFilter(obj, event)

    @QtCore.Slot()
    def quitApp(self):
        self.saveState()
        self.window.removeEventFilter(self)
        self.applicationQuitting = True
        QtCore.QThreadPool.globalInstance().waitForDone()
        app.quit()

    def show(self):
        self.window.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = MainWindowManager(app)
    w.show()
    sys.exit(app.exec_())
