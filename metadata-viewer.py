# This Python file uses the following encoding: utf-8
import sys
from PySide2 import QtCore, QtWidgets, QtUiTools, QtGui
from enum import Enum
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore.actions.DocumentActionManager import DocumentActionManager
from MetadataManagerCore.StateManager import StateManager
from MetadataManagerCore.actions.DocumentAction import DocumentAction

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
from VisualScripting import NodeGraphQt
from PySide2.QtCore import QFile, QTextStream, QThreadPool
from LoaderWindow import LoaderWindow

from assets import asset_manager
from qt_extensions.DockWidget import DockWidget
import os

from viewers.CollectionViewer import CollectionViewer
from viewers.PreviewViewer import PreviewViewer
from viewers.SettingsViewer import SettingsViewer
from viewers.Inspector import Inspector
from viewers.ActionsViewer import ActionsViewer
from viewers.DocumentActionManagerViewer import DocumentActionManagerViewer
from viewers.DeadlineServiceViewer import DeadlineServiceViewer
from viewers.EnvironmentManagerViewer import EnvironmentManagerViewer
from random import random

from VisualScripting.VisualScripting import VisualScripting
import VisualScriptingExtensions.mongodb_nodes
import VisualScriptingExtensions.document_action_nodes
import VisualScriptingExtensions.versioning_nodes
import VisualScriptingExtensions.third_party_extensions.deadline_nodes
import VisualScriptingExtensions.environment_nodes
from VisualScriptingExtensions.CodeGenerator import CodeGenerator

COMPANY = None
APP_NAME = None
MONGODB_HOST = None
DATABASE_NAME = None
SETTINGS = None
    
class Style(Enum):
    Dark = 0
    Light = 1

def constructTestCollection(dbManager : MongoDBManager):
    try:
        dbManager.db.drop_collection("Test_Collection")
        dbManager.db.drop_collection("Test_Collection" + Keys.OLD_VERSIONS_COLLECTION_SUFFIX)

        names = ["John", "Kevin", "Peter", "Klaus", "Leo"]
        for i in range(0,5):
            dbManager.insertOne("Test_Collection", { "name": names[i%len(names)], "address": f"Highway {i}" })
    except Exception as e:
        print(str(e))

class MainWindowManager(QtCore.QObject):
    def __init__(self, app):
        super(MainWindowManager, self).__init__()
        self.app = app
        self.currentStyle = None
        self.applicationQuitting = False
        self.documentMoficiations = []
        self.dbManager = None

        file = QtCore.QFile(asset_manager.getUIFilePath("main.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.window.installEventFilter(self)

        visualScriptingSaveDataFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "VisualScripting_SaveData")
        self.codeGenerator = CodeGenerator()
        self.visualScripting = VisualScripting(visualScriptingSaveDataFolder, parentWindow=self.window, codeGenerator=self.codeGenerator)

        self.setStyle(Style.Light)

        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

        self.settingsViewer = SettingsViewer(self.window)

        #self.initStatusInfo()

        self.collectionViewer = CollectionViewer(self.window)

        self.previewViewer = PreviewViewer(self.window)
        self.environmentManagerViewer = EnvironmentManagerViewer(self.window)

        self.inspector = Inspector(self.window)

        self.actionsViewer = ActionsViewer(self.window)
        self.actionsManagerViewer = DocumentActionManagerViewer(self.window)
        self.deadlineServiceViewer = DeadlineServiceViewer(self.window)
        VisualScriptingExtensions.third_party_extensions.deadline_nodes.DEADLINE_SERVICE = self.deadlineServiceViewer.deadlineService

        self.setupDockWidgets()

        self.window.findPushButton.clicked.connect(self.viewItems)

        self.restoreState()

    def initStatusInfo(self):
        self.mainProgressBar = QtWidgets.QProgressBar(self.window)
        self.mainProgressBar.setMaximumWidth(100)
        self.mainProgressBar.setMaximumHeight(15)
        self.window.statusBar().addPermanentWidget(self.mainProgressBar)

        #self.window.statusBar().showMessage("Test")

    def setup(self, dbManager):
        self.dbManager = dbManager

        self.stateManager = StateManager(self.dbManager)
        self.stateManager.loadState()
        self.actionManager = self.stateManager.actionManager

        self.codeGenerator.setActionManager(self.actionManager)

        VisualScriptingExtensions.mongodb_nodes.DB_MANAGER = dbManager
        self.visualScripting.updateNodeRegistration()

        #constructTestCollection(self.dbManager)
        self.collectionViewer.setDataBaseManager(self.dbManager)
        self.inspector.setDatabaseManager(self.dbManager)
        self.actionsViewer.setDatabaseManager(self.dbManager)
        self.actionsManagerViewer.setDataBaseManager(self.dbManager)

        self.collectionViewer.updateCollections()

        self.collectionViewer.restoreState(self.settings)

        header, displayedKeys = self.dbManager.extractTableHeaderAndDisplayedKeys(self.collectionViewer.yieldSelectedCollectionNames())
        self.tableModel = TableModel(self.window, [], header, displayedKeys)
        self.window.tableView.setModel(self.tableModel)

        selModel = self.window.tableView.selectionModel()
        selModel.selectionChanged.connect(self.onTableSelectionChanged)

        self.setupFilter()

        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.updateTableModelHeader)

        self.environmentManagerViewer.setup(self.stateManager.environmentManager, self.dbManager)

        self.actionsViewer.setup(self.actionManager, self, self.collectionViewer)
        self.actionsManagerViewer.setActionManager(self.actionManager)

        VisualScriptingExtensions.environment_nodes.ENVIRONMENT_MANAGER = self.stateManager.environmentManager

    def updateTableModelHeader(self):
        header, displayedKeys = self.dbManager.extractTableHeaderAndDisplayedKeys(self.collectionViewer.yieldSelectedCollectionNames())
        self.tableModel.updateHeader(header, displayedKeys)

    def applyAllDocumentModifications(self):
        if len(self.documentMoficiations) > 0:
            self.initDocumentProgress(len(self.documentMoficiations))
            progressCounter = 0
            self.updateDocumentProgress(progressCounter)

            for i in reversed(range(len(self.documentMoficiations))):
                progressCounter += 1
                self.documentMoficiations[i].applyModification()
                self.documentMoficiations.pop()
                self.updateDocumentProgress(progressCounter)

    def setupDockWidgets(self):
        self.setupDockWidget(self.previewViewer)
        
        self.setupDockWidget(self.collectionViewer, initialDockArea=QtCore.Qt.LeftDockWidgetArea)
        self.setupDockWidget(self.settingsViewer, initialDockArea=QtCore.Qt.LeftDockWidgetArea)
        self.setupDockWidget(self.visualScripting.getAsDockWidget(self.window), initialDockArea=QtCore.Qt.BottomDockWidgetArea)

        self.setupDockWidget(self.inspector)
        self.setupDockWidget(self.actionsViewer)
        self.setupDockWidget(self.actionsManagerViewer)
        self.setupDockWidget(self.deadlineServiceViewer)
        self.setupDockWidget(self.environmentManagerViewer)

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

    @property
    def selectedDocumentIds(self):
        for rowIdx in self.window.tableView.selectionModel().selectedRows():
            yield self.tableModel.getUID(rowIdx.row())

    def onTableSelectionChanged(self, newSelection, oldSelection):
        #selectedRows = set([idx.row() for sel in newSelection for idx in sel.indexes()])
        selectedRows = self.window.tableView.selectionModel().selectedRows()
        #newSelectedRows = set([idx.row() for idx in newSelection.indexes()])

        if len(selectedRows) > 0:
            lastSelectedRowIdx = selectedRows[-1].row()
            uid = self.tableModel.getUID(lastSelectedRowIdx)
            item = self.dbManager.findOne(uid)
            if item != None:
                self.previewViewer.showPreview(item.get("preview"))
                self.inspector.showItem(uid)

    def addPreviewToAllEntries(self):
        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
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

    def getFilteredDocumentsOfCollection(self, collectionName):
        for d in self.dbManager.getFilteredDocuments(collectionName, self.getItemsFilter(), distinctionText=self.window.distinctEdit.text()):
            yield d

    def getMaxDisplayedTableItems(self):
        num = 0
        filter = self.getItemsFilter()
        distinctKey = self.window.distinctEdit.text()

        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            if len(distinctKey) > 0:
                num += len(collection.find(self.getItemsFilter()).distinct(distinctKey))
            else:
                num += collection.count_documents(filter)

        return num

    def initDocumentProgress(self, maxVal):
        qt_util.runInMainThread(self.window.documentProgressBar.setMaximum, maxVal)

    def updateDocumentProgress(self, val):
        qt_util.runInMainThread(self.window.documentProgressBar.setValue, val)

    @timeit
    def viewItems(self):
        #self.dbManager.insertOrModifyDocument("Test_Collection", "paul", {"name":"Paul", "address":f"Litauen{str(random())}", "some_other_entry":5})

        if len(self.tableModel.displayedKeys) == 0:
            return

        qt_util.runInMainThread(self.window.findPushButton.setEnabled, False)

        qt_util.runInMainThread(self.tableModel.clear)
        maxDisplayedItems = self.getMaxDisplayedTableItems()
        qt_util.runInMainThread(lambda:self.window.itemCountLabel.setText("Item Count: " + str(maxDisplayedItems)))

        if maxDisplayedItems == 0:
            qt_util.runInMainThread(self.window.findPushButton.setEnabled, True)
            return
        
        self.initDocumentProgress(maxDisplayedItems)

        entries = []
        i = 0
        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
            for item in self.getFilteredDocumentsOfCollection(collectionName):
                if self.applicationQuitting:
                    return

                i += 1
                tableEntry = self.extractTableEntry(self.tableModel.displayedKeys, item)
                entries.append(tableEntry)
                self.updateDocumentProgress(i)
        
        qt_util.runInMainThread(self.tableModel.addEntries, entries)
        qt_util.runInMainThread(self.updateDocumentProgress, 0.0)

        qt_util.runInMainThread(self.window.findPushButton.setEnabled, True)

    def getFilteredDocuments(self):
        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
            for d in self.getFilteredDocumentsOfCollection(collectionName):
                yield d

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

        if (style == Style.Dark) and self.currentStyle != style:
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
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Button, QtGui.QColor(25, 25, 25))
            self.app.setPalette(palette)
        elif (style == Style.Light or style == None) and self.currentStyle != style:
            self.app.setStyleSheet(None)
            self.app.setPalette(QtWidgets.QApplication.style().standardPalette())

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

        settings.setValue("geometry", self.window.saveGeometry())
        settings.setValue("windowState", self.window.saveState())
        settings.setValue("style", self.currentStyle)
        self.visualScripting.saveWindowState(settings)
        self.collectionViewer.saveState(settings)

        self.stateManager.saveState()
        self.deadlineServiceViewer.saveState(settings)

    def restoreState(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(COMPANY, APP_NAME)

        self.settings = settings
        self.window.restoreGeometry(settings.value("geometry"))
        self.window.restoreState(settings.value("windowState"))
        self.setStyle(settings.value("style"))
        self.visualScripting.restoreWindowState(settings)
        self.deadlineServiceViewer.restoreState(settings)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QtCore.QEvent.Close:
            self.quitApp()
            event.ignore()
            return True
        return super(MainWindowManager, self).eventFilter(obj, event)

    @QtCore.Slot()
    def quitApp(self, bSaveState = True):
        if bSaveState:
            self.saveState()
        self.window.removeEventFilter(self)
        self.applicationQuitting = True
        QtCore.QThreadPool.globalInstance().waitForDone()
        app.quit()

    def show(self):
        self.window.showMaximized()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    SETTINGS = QtCore.QSettings(asset_manager.getMainSettingsPath(), QtCore.QSettings.IniFormat)

    COMPANY = SETTINGS.value("company")
    APP_NAME = SETTINGS.value("app_name")
    MONGODB_HOST = SETTINGS.value("mongodb_host")
    DATABASE_NAME = SETTINGS.value("db_name")

    mainWindow = MainWindowManager(app)

    loaderWindow = LoaderWindow(app, mainWindow, MONGODB_HOST, DATABASE_NAME)

    sys.exit(app.exec_())
