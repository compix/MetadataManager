# This Python file uses the following encoding: utf-8
import sys
from viewers.HostProcessViewer import HostProcessViewer
from viewers.service.ServiceManagerViewer import ServiceManagerViewer
from PySide2 import QtCore, QtWidgets, QtUiTools, QtGui
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
from MetadataManagerCore import Keys
from VisualScripting.VisualScriptingViewer import VisualScriptingViewer
from PySide2.QtCore import QFile, QTextStream, QThreadPool

import asset_manager
from qt_extensions.DockWidget import DockWidget
import os

from viewers.CollectionViewer import CollectionViewer
from viewers.PreviewViewer import PreviewViewer
from viewers.SettingsViewer import SettingsViewer
from viewers.Inspector import Inspector
from viewers.ActionsViewer import ActionsViewer
from viewers.ActionManagerViewer import ActionManagerViewer
from viewers.DeadlineServiceViewer import DeadlineServiceViewer
from viewers.EnvironmentManagerViewer import EnvironmentManagerViewer
from viewers.DocumentSearchFilterViewer import DocumentSearchFilterViewer
from random import random

from typing import List
from AppInfo import AppInfo

from custom import *

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

        self.restoreState()

    def initTable(self):
        self.tableModel = TableModel(self.window, [], [], [])
        self.window.tableView.setModel(self.tableModel)

        selModel = self.window.tableView.selectionModel()
        selModel.selectionChanged.connect(self.onTableSelectionChanged)

    def initViewers(self):
        self.visualScriptingViewer = VisualScriptingViewer(self.serviceRegistry.visualScripting)
        self.visualScriptingViewer.updateNodeRegistration()

        self.settingsViewer = SettingsViewer(self.window)
        self.collectionViewer = CollectionViewer(self.window, self.serviceRegistry.dbManager)
        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.updateTableModelHeader)
        self.collectionViewer.headerUpdatedEvent.subscribe(self.updateTableModelHeader)

        self.previewViewer = PreviewViewer(self.window)
        settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)
        self.environmentManagerViewer = EnvironmentManagerViewer(self.window, self.serviceRegistry.environmentManager, 
                                                                 self.serviceRegistry.dbManager, settings)
        self.inspector = Inspector(self.window, self.serviceRegistry.dbManager)
        self.actionsViewer = ActionsViewer(self.window, self.serviceRegistry.dbManager, self.serviceRegistry.actionManager, 
                                           self, self.collectionViewer, self.visualScriptingViewer)
        self.actionsManagerViewer = ActionManagerViewer(self.window, self.serviceRegistry.actionManager, self.serviceRegistry.dbManager)
        self.deadlineServiceViewer = DeadlineServiceViewer(self.window, self.serviceRegistry.deadlineService)

        self.documentSearchFilterViewer = DocumentSearchFilterViewer(self.appInfo, self.window, self.dbManager, 
                                                                     self.serviceRegistry.documentFilterManager, 
                                                                     self.tableModel, self.collectionViewer)
        self.window.documentSearchFilterFrame.layout().addWidget(self.documentSearchFilterViewer.widget)

        self.serviceManagerViewer = ServiceManagerViewer(self.window, self.serviceRegistry)

        self.hostProcessViewer = HostProcessViewer(self.window, self.serviceRegistry.hostProcessController)

    def setupEventAndActionHandlers(self):
        self.window.installEventFilter(self)
        
        self.window.actionDark.triggered.connect(lambda : self.setStyle(Style.Dark))
        self.window.actionLight.triggered.connect(lambda : self.setStyle(Style.Light))

    def initStatusInfo(self):
        self.mainProgressBar = QtWidgets.QProgressBar(self.window)
        self.mainProgressBar.setMaximumWidth(100)
        self.mainProgressBar.setMaximumHeight(15)
        self.window.statusBar().addPermanentWidget(self.mainProgressBar)

        #self.window.statusBar().showMessage("Test")

    def updateTableModelHeader(self):
        headerInfos = self.dbManager.extractCollectionHeaderInfo(self.collectionViewer.yieldSelectedCollectionNames())
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



    def showItemInInspector(self, uid):
        form = self.window.inspectorFormLayout
        qt_util.clearContainer(form)
        item = self.dbManager.findOne(uid)
        if item != None:
            for key, val in item.items():
                form.addRow(self.window.tr(str(key)), QtWidgets.QLabel(str(val)))

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
            disabledColor = QtGui.QColor(25, 25, 25)
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