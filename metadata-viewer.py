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
from qt_extensions import qt_util
import json
import numpy as np
import pymongo
from TableModel import TableModel
from qt_extensions.Completer import Completer
from MetadataManagerCore import Keys
from VisualScripting.VisualScripting import VisualScripting
from VisualScripting import NodeGraphQt
from PySide2.QtCore import QFile, QTextStream

from assets import asset_manager
from qt_extensions.DockWidget import DockWidget

from viewers.CollectionViewer import CollectionViewer
from viewers.PreviewViewer import PreviewViewer
from viewers.SettingsViewer import SettingsViewer
from viewers.Inspector import Inspector


COMPANY = "WK"
APP_NAME = "Metadata-Manager"
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

        file = QtCore.QFile(asset_manager.getUIFilePath("main.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.window.installEventFilter(self)

        self.visualScripting = VisualScripting("VisualScripting_SaveData", parentWindow=self.window)

        self.setStyle(Style.Light)

        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

        self.dbManager = MongoDBManager(mongodbHost, databaseName)

        constructTestCollection(self.dbManager)

        self.settingsViewer = SettingsViewer(self.window)

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

        self.previewViewer = PreviewViewer(self.window)

        self.inspector = Inspector(self.window, self.dbManager)

        self.setupDockWidgets()

        #self.window.findPushButton.clicked.connect(lambda:QThreadPool.globalInstance().start(LambdaTask(self.viewItems)))
        self.window.findPushButton.clicked.connect(self.viewItems)

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
        self.setupDockWidget(self.previewViewer)
        
        self.setupDockWidget(self.window.actionsDockWidget)
        self.setupDockWidget(self.collectionViewer, initialDockArea=QtCore.Qt.LeftDockWidgetArea)
        self.setupDockWidget(self.window.commentsDockWidget)
        self.setupDockWidget(self.settingsViewer, initialDockArea=QtCore.Qt.LeftDockWidgetArea)
        self.setupDockWidget(self.visualScripting.getAsDockWidget(self.window), initialDockArea=QtCore.Qt.BottomDockWidgetArea)

        self.setupDockWidget(self.inspector)

    def setupDockWidget(self, dockWidget : DockWidget, initialDockArea=None):
        # Add visibility checkbox to view main menu:
        self.window.menuView.addAction(dockWidget.toggleViewAction())
        # Allow window functionality (e.g. maximize)
        dockWidget.topLevelChanged.connect(self.dockWidgetTopLevelChanged)
        self.setDockWidgetFlags(dockWidget)

        if initialDockArea != None:
            self.window.addDockWidget(initialDockArea, dockWidget)
        else:
            self.window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dockWidget)
            dockWidget.toggleViewAction()

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
                    self.previewViewer.show(item.get("preview"))
                    self.inspector.showItem(uid)

    def addPreviewToAllEntries(self):
        for collectionName in self.collectionViewer.getSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            for item in collection.find({}):
                collection.update_one({"_id":item["_id"]}, {"$set": {"preview":"C:/Users/compix/Desktop/surprised_pikachu.png"}})

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
        qt_util.clearContainer(form)
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

        self.window.actionSave_Default_Layout.triggered.connect(self.saveDefaultLayout)
        self.window.actionRestore_Default_Layout.triggered.connect(self.restoreDefaultLayout)
        
    def saveDefaultLayout(self):
        settings = QtCore.QSettings(asset_manager.getDefaultLayoutFilePath("default.ini"), QtCore.QSettings.IniFormat)
        self.saveState(settings)

    def restoreDefaultLayout(self):
        settings = QtCore.QSettings(asset_manager.getDefaultLayoutFilePath("default.ini"), QtCore.QSettings.IniFormat)
        self.restoreState(settings)

    def saveState(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(COMPANY, APP_NAME)

        print(settings.fileName())
        settings.setValue("geometry", self.window.saveGeometry())
        settings.setValue("windowState", self.window.saveState())
        settings.setValue("style", self.currentStyle)
        self.visualScripting.saveWindowState(settings)
        self.collectionViewer.saveState(settings)

    def restoreState(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(COMPANY, APP_NAME)

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
        self.window.showMaximized()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = MainWindowManager(app)
    w.show()
    sys.exit(app.exec_())
