# This Python file uses the following encoding: utf-8
import sys
from MetadataManagerCore.actions.ActionType import ActionType

from viewers.HostProcessViewer import HostProcessViewer
from viewers.service.ServiceManagerViewer import ServiceManagerViewer
from PySide2 import QtCore, QtWidgets, QtUiTools, QtGui
from PySide2.QtCore import Qt
from enum import Enum
from MetadataManagerCore.mongodb_manager import CollectionHeaderKeyInfo, MongoDBManager
from qt_extensions import qt_util
from TableModel import TableModel
from MetadataManagerCore import Keys
from VisualScripting.VisualScriptingViewer import VisualScriptingViewer

import asset_manager
from qt_extensions.DockWidget import DockWidget

from viewers.CollectionViewer import CollectionViewer
from viewers.PreviewViewer import PreviewViewer
from viewers.SettingsViewer import SettingsViewer
from viewers.Inspector import Inspector
from viewers.ActionsViewer import ActionsViewer
from viewers.ActionManagerViewer import ActionManagerViewer
from viewers.DeadlineServiceViewer import DeadlineServiceViewer
from viewers.EnvironmentManagerViewer import EnvironmentManagerViewer
from viewers.DocumentSearchFilterViewer import DocumentSearchFilterViewer
from viewers.PluginManagerViewer import PluginManagerViewer
from viewers.ViewerRegistry import ViewerRegistry
import os
from datetime import datetime
from typing import List
from AppInfo import AppInfo

import logging
from ServiceRegistry import ServiceRegistry

logger = logging.getLogger(__name__)

class Style(Enum):
    Dark = 0
    Light = 1

class MainWindowManager(QtCore.QObject):
    def __init__(self, app, appInfo : AppInfo, serviceRegistry : ServiceRegistry, bootstrapper):
        super(MainWindowManager, self).__init__()
        self.app = app
        self.appInfo = appInfo
        self.currentStyle = None
        self.documentMoficiations = []
        self.dockWidgets : List[DockWidget] = []
        self.serviceRegistry = serviceRegistry
        self.dbManager = self.serviceRegistry.dbManager
        self.bootstrapper = bootstrapper
        self.viewerRegistry = ViewerRegistry()

        self.viewerRegistry.mainWindowManager = self

        # Load the main window ui
        file = QtCore.QFile(asset_manager.getUIFilePath("main.ui"))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.window = loader.load(file)

        self.setStyle(Style.Light)

        self.initTable()

        self.initViewers()

        self.setupDockWidgets()
        self.setupEventAndActionHandlers()

        self.addSplitter()
        self.restoreState()

        self.documentSearchFilterViewer.viewItemsOverThreadPool(saveSearchHistoryEntry=False)

    def addSplitter(self):
        mainFrame: QtWidgets.QFrame = self.window.main_frame
        self.splitter = QtWidgets.QSplitter()
        mainFrame.layout().addWidget(self.splitter)
        self.splitter.setOrientation(Qt.Vertical)
        mainFrame.layout().removeWidget(self.window.documentSearchFilterFrame)
        mainFrame.layout().removeWidget(self.window.tableViewFrame)
        self.splitter.addWidget(self.window.documentSearchFilterFrame)
        self.splitter.addWidget(self.window.tableViewFrame)
        self.splitter.setOpaqueResize(False)
        self.splitter.setCollapsible(1, False)

    @property
    def tabWidget(self) -> QtWidgets.QTabWidget:
        return self.window.tabWidget

    @property
    def menuBar(self) -> QtWidgets.QMenuBar:
        return self.window.menubar

    def refreshTableViewContextMenu(self):
        self.tableViewContextMenu.clear()
        for task in self.actionsViewer.actionTasks:
            if task.action.actionType == ActionType.DocumentAction:
                action = QtWidgets.QAction(task.action.displayName, self.tableView)
                self.tableViewContextMenu.addAction(action)
                action.triggered.connect(task)

    def initTable(self):
        self.currentVisualHeaderIndices = None
        self.tableModel = TableModel(self.window, [], [], [])
        self.window.tableView.setModel(self.tableModel)

        selModel = self.window.tableView.selectionModel()
        selModel.selectionChanged.connect(self.onTableSelectionChanged)

        self.tableView: QtWidgets.QTableView = self.window.tableView
        self.tableView.customContextMenuRequested.connect(self.contextMenuEvent)
        self.tableViewContextMenu = QtWidgets.QMenu(self.tableView)
        self.tableView.horizontalHeader().setSectionsMovable(True)
        self.tableView.horizontalHeader().sectionMoved.connect(self.onSectionMoved)

    def onSectionMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        # Save order in db
        selectedCollectionNames = self.collectionViewer.getSelectedCollectionNames()
        if len(selectedCollectionNames) != 1:
            return

        collectionName = selectedCollectionNames[0]
        headerInfos = self.dbManager.extractCollectionHeaderInfo(selectedCollectionNames)
        handledKeys = set()
        keyToHeaderInfo = {
            i.key:i for i in headerInfos
        }

        newHeaderKeyInfos = []
        for i in range(len(self.tableModel.header)):
            logicalIdx = self.tableView.horizontalHeader().logicalIndex(i)
            key = self.tableModel.displayedKeys[logicalIdx]
            headerInfo = keyToHeaderInfo.get(key)
            if headerInfo:
                newHeaderKeyInfos.append(headerInfo)
                handledKeys.add(key)
        
        for i in headerInfos:
            if not i.key in handledKeys:
                newHeaderKeyInfos.append(i)

        self.dbManager.setCollectionHeaderInfo(collectionName, newHeaderKeyInfos)

    def contextMenuEvent(self):
        self.refreshTableViewContextMenu()
        self.tableViewContextMenu.exec_(QtGui.QCursor.pos())

    def copyTableSelection(self):
        selection = self.window.tableView.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = str(index.data()) if index.data() else ''

            csv = ""
            for row in table:
                csv += '\t'.join(row) + '\n'

            cb = QtWidgets.QApplication.clipboard()
            cb.clear(mode=cb.Clipboard)
            cb.setText(csv, mode=cb.Clipboard)

    def initViewers(self):
        self.visualScriptingViewer = VisualScriptingViewer(self.serviceRegistry.visualScripting)
        self.visualScriptingViewer.updateNodeRegistration()

        self.settingsViewer = SettingsViewer(self.window, self.serviceRegistry)
        self.collectionViewer = CollectionViewer(self.window, self.serviceRegistry.dbManager)
        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.updateTableModelHeader)
        self.collectionViewer.headerUpdatedEvent.subscribe(self.updateTableModelHeader)

        self.previewViewer = PreviewViewer(self.window)
        self.environmentManagerViewer = EnvironmentManagerViewer(self.window, self.serviceRegistry.environmentManager, 
                                                                 self.serviceRegistry.dbManager)
        self.inspector = Inspector(self.window, self.serviceRegistry.dbManager, self.collectionViewer)
        self.actionsViewer = ActionsViewer(self.window, self.serviceRegistry.dbManager, self.serviceRegistry.actionManager, 
                                           self, self.collectionViewer, self.visualScriptingViewer)
        self.actionsManagerViewer = ActionManagerViewer(self.window, self.serviceRegistry.actionManager, self.serviceRegistry.dbManager, self.collectionViewer)
        self.deadlineServiceViewer = DeadlineServiceViewer(self.window, self.serviceRegistry.deadlineService)

        self.documentSearchFilterViewer = DocumentSearchFilterViewer(self.appInfo, self.window, self.dbManager, 
                                                                     self.serviceRegistry.documentFilterManager, 
                                                                     self.tableModel, self.collectionViewer)
        self.window.documentSearchFilterFrame.layout().addWidget(self.documentSearchFilterViewer.widget)

        self.serviceManagerViewer = ServiceManagerViewer(self.window, self.serviceRegistry)

        self.hostProcessViewer = HostProcessViewer(self.window, self.serviceRegistry.hostProcessController)

        self.pluginManagerViewer = PluginManagerViewer(self.window, self.serviceRegistry.pluginManager, self.bootstrapper.requestRestart)
        self.serviceRegistry.pluginManager.setViewerRegistry(self.viewerRegistry)

        # Setup viewer registry:
        self.viewerRegistry.actionManagerViewer = self.actionsManagerViewer
        self.viewerRegistry.actionsViewer = self.actionsViewer
        self.viewerRegistry.collectionViewer = self.collectionViewer
        self.viewerRegistry.deadlineServiceViewer = self.deadlineServiceViewer
        self.viewerRegistry.documentSearchFilterViewer = self.documentSearchFilterViewer
        self.viewerRegistry.environmentManagerViewer = self.environmentManagerViewer
        self.viewerRegistry.hostProcessViewer = self.hostProcessViewer
        self.viewerRegistry.pluginManagerViewer = self.pluginManagerViewer
        self.inspector = self.inspector
        self.viewerRegistry.settingsViewer = self.settingsViewer
        self.viewerRegistry.previewViewer = self.previewViewer
        self.viewerRegistry.inspector = self.inspector
        self.viewerRegistry.visualScriptingViewer = self.visualScriptingViewer

    def setupEventAndActionHandlers(self):
        self.window.installEventFilter(self)
        
        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

    def updateTableModelHeader(self):
        headerInfos = self.dbManager.extractCollectionHeaderInfo(self.collectionViewer.getSelectedCollectionNames())
        displayedHeaderInfos = [i for i in headerInfos if i.displayed]
        self.tableModel.updateHeader([i.displayName for i in displayedHeaderInfos], [i.key for i in displayedHeaderInfos])

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
        self.setupDockWidget(self.visualScriptingViewer.getAsDockWidget(self.window), initialDockArea=QtCore.Qt.BottomDockWidgetArea)
        self.setupDockWidget(self.visualScriptingViewer.getSettingsAsDockWidget(), initialDockArea=QtCore.Qt.BottomDockWidgetArea)

        self.setupDockWidget(self.inspector)
        self.setupDockWidget(self.actionsViewer)
        self.setupDockWidget(self.actionsManagerViewer)
        self.setupDockWidget(self.deadlineServiceViewer)
        self.setupDockWidget(self.environmentManagerViewer)
        self.setupDockWidget(self.serviceManagerViewer)
        self.setupDockWidget(self.hostProcessViewer)
        self.setupDockWidget(self.pluginManagerViewer)

    def setupDockWidget(self, dockWidget : DockWidget, initialDockArea=None):
        self.dockWidgets.append(dockWidget)

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
            dockWidget.setVisible(False)

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

    def getFilteredDocuments(self):
        return self.documentSearchFilterViewer.getFilteredDocuments()

    def onTableSelectionChanged(self, newSelection, oldSelection):
        selectedRows = self.window.tableView.selectionModel().selectedRows()
        selectedCount = len(selectedRows)

        if selectedCount > 0:
            lastSelectedRowIdx = selectedRows[-1].row()
            uid = self.tableModel.getUID(lastSelectedRowIdx)
            item = self.dbManager.findOneInCollections(uid, self.collectionViewer.getSelectedCollectionNames())
            if item != None:
                self.previewViewer.showPreview(item.get(Keys.preview))
                self.showItem(uid)

        self.window.selectedItemCountLabel.setText(f'Selected Count: {selectedCount}')

    def showItem(self, uid: str):
        itemDict = self.dbManager.findOneInCollections(uid, self.collectionViewer.getSelectedCollectionNames())

        if not itemDict:
            self.inspector.showDictionary({})
            return

        previewFilename = itemDict.get('preview')
        if previewFilename and os.path.exists(previewFilename):
            stats = os.stat(previewFilename)
            fileInfoDict = dict()
            fileInfoDict['File Created'] = datetime.fromtimestamp(stats.st_ctime).strftime("%d.%m.%Y %H:%M:%S")
            fileInfoDict['File Modified'] = datetime.fromtimestamp(stats.st_mtime).strftime("%d.%m.%Y %H:%M:%S")

            fileSize = float(stats.st_size)
            fileSizeInKb = fileSize / 1024.0
            fileSizeInMb = fileSizeInKb / 1024.0
            if int(round(fileSizeInMb)) > 0:
                fileInfoDict['File Size'] = f'{int(round(fileSizeInMb))} MB'
            elif int(round(fileSizeInKb)) > 0:
                fileInfoDict['File Size'] = f'{int(round(fileSizeInKb))} KB'
            else:
                fileInfoDict['File Size'] = f'{int(round(fileSizeInKb))} B'

            dataDict = {**itemDict, **fileInfoDict}
            self.inspector.showDictionary(dataDict)
        else:
            self.inspector.showDictionary(itemDict)

    def extractSystemValues(self, item):
        vals = []
        for sysKey in Keys.systemKeys:
            val = item.get(sysKey)
            vals.append(val if val != None else Keys.notDefinedValue)
        
        return vals

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
            disabledColor = QtGui.QColor(35, 35, 35)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Window, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Base, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Button, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Link, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, disabledColor)
            palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, disabledColor)
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
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)

        settings.setValue("geometry", self.window.saveGeometry())
        settings.setValue("windowState", self.window.saveState())
        settings.setValue("style", self.currentStyle)

        settings.setValue("main_splitter_geo", self.splitter.saveGeometry())
        settings.setValue("main_splitter_state", self.splitter.saveState())

        for dockWidget in self.dockWidgets:
            if isinstance(dockWidget, DockWidget):
                dockWidget.saveState(settings)

        self.documentSearchFilterViewer.saveState(settings)

    def restoreState(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)

        self.settings = settings
        self.window.restoreGeometry(settings.value("geometry"))
        self.window.restoreState(settings.value("windowState"))
        self.splitter.restoreGeometry(settings.value("main_splitter_geo"))
        self.splitter.restoreState(settings.value("main_splitter_state"))

        try:
            self.setStyle(settings.value("style", Style.Dark))
        except:
            self.setStyle(Style.Dark)

        for dockWidget in self.dockWidgets:
            if isinstance(dockWidget, DockWidget):
                dockWidget.restoreState(settings)

        self.documentSearchFilterViewer.restoreState(settings)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QtCore.QEvent.Close:
            self.quitApp()
            event.ignore()
            return True

        if event.type() == QtCore.QEvent.ShortcutOverride and event.matches(QtGui.QKeySequence.Copy):
            self.copyTableSelection()
            return True

        return super(MainWindowManager, self).eventFilter(obj, event)

    def close(self):
        self.window.close()
        
    @QtCore.Slot()
    def quitApp(self, bSaveState = True):
        if bSaveState:
            self.saveState()
        self.window.removeEventFilter(self)
        self.appInfo.applicationQuitting = True
        logger.info("Quitting application...")
        
        self.bootstrapper.shutdown()
        self.app.quit()

    def show(self):
        self.window.showMaximized()