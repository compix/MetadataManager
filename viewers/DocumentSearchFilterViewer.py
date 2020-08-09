import PySide2
import asset_manager
from qt_extensions import qt_util
from TableModel import TableModel
from viewers.CollectionViewer import CollectionViewer
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore import Keys
from AppInfo import AppInfo
import logging
from qt_extensions.Completer import Completer
from PySide2 import QtCore, QtWidgets
from PySide2.QtWidgets import QCheckBox, QListWidget, QListWidgetItem, QHBoxLayout, QLineEdit, QWidget, QLayout, QAbstractItemView, QVBoxLayout
from PySide2 import QtGui
from PySide2.QtCore import QThreadPool
import json
from typing import List
import os
import re
from MetadataManagerCore.util import timeit
from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager

class DocumentFilterView(object):
    def __init__(self, documentFilter : DocumentFilter):
        self.documentFilter = documentFilter

        self.activeCheckBox = QCheckBox()
        self.activeCheckBox.stateChanged.connect(self.onActiveCheckBoxChanged)
        self.activeCheckBox.setText(self.documentFilter.uniqueFilterLabel)

        self.negateCheckBox = QCheckBox()
        self.negateCheckBox.stateChanged.connect(self.onNegateCheckBoxChanged)
        self.negateCheckBox.setText('Negate')

        self.container = QWidget()
        layout = QHBoxLayout()
        self.container.setLayout(layout)
        self.container.layout().addWidget(self.activeCheckBox)
        self.container.layout().addWidget(self.negateCheckBox)

        if documentFilter.hasStringArg:
            self.textEdit = QLineEdit()
            self.textEdit.textChanged.connect(self.onTextEditChanged)
            self.container.layout().addWidget(self.textEdit)

        self.container.layout().setAlignment(QtCore.Qt.AlignLeft)
        self.container.adjustSize()

        self.container.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        self.container.setFixedHeight(20)
    
    def isFilterActive(self):
        return self.activeCheckBox.isChecked() if not self.negateCheckBox.isChecked() else not self.activeCheckBox.isChecked()

    def onActiveCheckBoxChanged(self, _):
        self.documentFilter.setActive(self.activeCheckBox.isChecked())
    
    def onNegateCheckBoxChanged(self, _):
        self.documentFilter.setNegateFilter(self.negateCheckBox.isChecked())

    def onTextEditChanged(self, text):
        self.documentFilter.setArgs(text)

class DocumentSearchFilterViewer(QtCore.QObject):
    def __init__(self, appInfo : AppInfo, mainWindow, dbManager : MongoDBManager, documentFilterManager : DocumentFilterManager, 
                 documentTableModel : TableModel, collectionViewer : CollectionViewer):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.widget = asset_manager.loadUIFile('documentSearchFilter.ui')

        self.appInfo = appInfo
        self.mainWindow = mainWindow
        self.dbManager = dbManager
        self.documentFilterManager = documentFilterManager
        self.documentTableModel = documentTableModel
        self.collectionViewer = collectionViewer
        self.documentFilterViews : List[DocumentFilterView] = []

        self.customFilterScrollAreaLayout : QVBoxLayout = self.widget.customFilterScrollAreaLayout
        self.customFilterScrollAreaLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.findPushButton.clicked.connect(lambda: QThreadPool.globalInstance().start(qt_util.LambdaTask(self.viewItems)))

        self.setupFilter()
        self.updateDisplayedFilters()

        self.documentFilterManager.onFilterListUpdateEvent.subscribe(self.updateDisplayedFilters)

    def setupFilter(self):
        wordList = [("\"" + f + "\"") for f in self.documentTableModel.displayedKeys]
        filterCompleter = Completer(wordList, self)
        filterCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filterCompleter.setFilterMode(QtCore.Qt.MatchContains)
        filterCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.widget.filterEdit.setCompleter(filterCompleter)

        wordList = [f for f in self.documentTableModel.displayedKeys]
        distinctCompleter = Completer(wordList, self)
        distinctCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        distinctCompleter.setFilterMode(QtCore.Qt.MatchContains)
        distinctCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.widget.distinctEdit.setCompleter(distinctCompleter)

    def updateDisplayedFilters(self):
        self.documentFilterViews.clear()
        qt_util.clearContainer(self.customFilterScrollAreaLayout)

        for docFilter in self.documentFilterManager.customFilters:
            filterView = DocumentFilterView(docFilter)
            self.documentFilterViews.append(filterView)
            self.customFilterScrollAreaLayout.addWidget(filterView.container)

    def getFilteredDocumentsOfCollection(self, collectionName):
        for d in self.documentFilterManager.yieldFilteredDocuments(collectionName, self.getItemsFilter(), 
                                                                   distinctionText=self.widget.distinctEdit.text(), 
                                                                   filters=self.documentFilterManager.customFilters):
            yield d

    def getItemsFilter(self):
        try:
            filterText = self.widget.filterEdit.text()
            if len(self.widget.filterEdit.text()) == 0:
                return {}
            
            filterDict = json.loads(filterText)
            return filterDict
        except Exception as e:
            self.logger.error(f'Could not extract filter dictionary. Reason: {str(e)}')
            return {"_id":"None"}

    def getMaxDisplayedTableItems(self):
        num = 0
        filterDict = self.getItemsFilter()
        distinctKey = self.widget.distinctEdit.text()

        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
            collection = self.dbManager.db[collectionName]
            if len(distinctKey) > 0:
                num += len(collection.find(self.getItemsFilter()).distinct(distinctKey))
            else:
                num += collection.count_documents(filterDict)

        return num

    def updateDocumentProgress(self, val):
        qt_util.runInMainThread(self.widget.documentProgressBar.setValue, val)

    def getFilteredDocuments(self):
        for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
            for d in self.getFilteredDocumentsOfCollection(collectionName):
                yield d

    def initDocumentProgress(self, maxVal):
        if not isinstance(maxVal, int):
            maxVal = 0
            
        qt_util.runInMainThread(self.widget.documentProgressBar.setMaximum, maxVal)

    # item: mongodb document
    def extractTableEntry(self, displayedKeys, item):
        assert(len(displayedKeys) > 0)
        entry = [item['_id']]
        for e in displayedKeys:
            val = item.get(e)
            entry.append(val if val != None else Keys.notDefinedValue)

        return entry

    @timeit
    def viewItems(self):
        if len(self.documentTableModel.displayedKeys) == 0:
            return

        qt_util.runInMainThread(self.widget.findPushButton.setEnabled, False)

        qt_util.runInMainThread(self.documentTableModel.clear)
        maxDisplayedItems = "computing..."
        qt_util.runInMainThread(lambda: self.mainWindow.itemCountLabel.setText("Item Count: " + str(maxDisplayedItems)))

        if maxDisplayedItems == 0:
            qt_util.runInMainThread(self.widget.findPushButton.setEnabled, True)
            return
        
        self.initDocumentProgress(maxDisplayedItems)
        self.updateDocumentProgress(1)

        entries = []
        i = 0
        try:
            for collectionName in self.collectionViewer.yieldSelectedCollectionNames():
                for item in self.getFilteredDocumentsOfCollection(collectionName):
                    if self.appInfo.applicationQuitting:
                        return

                    i += 1
                    tableEntry = self.extractTableEntry(self.documentTableModel.displayedKeys, item)
                    entries.append(tableEntry)
        except Exception as e:
            self.logger.error(f'Failed to retrieve filtered items. Reason: {str(e)}')
        
        qt_util.runInMainThread(self.documentTableModel.addEntries, entries)
        self.initDocumentProgress(i if i > 0 else 1)
        qt_util.runInMainThread(lambda:self.mainWindow.itemCountLabel.setText("Item Count: " + str(i)))
        self.updateDocumentProgress(0.0)

        qt_util.runInMainThread(self.widget.findPushButton.setEnabled, True)