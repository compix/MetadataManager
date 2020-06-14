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
from PySide2.QtWidgets import QCheckBox, QListWidget, QListWidgetItem
from PySide2.QtCore import QThreadPool
import json
from typing import List
import os
import re
from MetadataManagerCore.util import timeit

class CustomFilter(object):
    def __init__(self, checkbox, filterFunction):
        self.checkbox = checkbox
        self.filterFunction = filterFunction

class DocumentSearchFilterViewer(QtCore.QObject):
    def __init__(self, appInfo : AppInfo, mainWindow, dbManager : MongoDBManager, 
                 documentTableModel : TableModel, collectionViewer : CollectionViewer):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.widget = asset_manager.loadUIFile('documentSearchFilter.ui')

        self.appInfo = appInfo
        self.mainWindow = mainWindow
        self.dbManager = dbManager
        self.documentTableModel = documentTableModel
        self.collectionViewer = collectionViewer
        self.customFilters : List[CustomFilter] = []
        self.customFilterListWidget : QListWidget = self.widget.customFilterListWidget

        self.widget.findPushButton.clicked.connect(lambda: QThreadPool.globalInstance().start(qt_util.LambdaTask(self.viewItems)))
        #self.widget.findPushButton.clicked.connect(self.viewItems)

        self.setupFilter()

    def addCustomFilter(self, filterText, filterFunction):
        checkbox = QCheckBox()
        checkbox.setText(filterText)
        item = QListWidgetItem()

        self.customFilterListWidget.addItem(item)
        self.customFilterListWidget.setItemWidget(item, checkbox)
        customFilter = CustomFilter(checkbox, filterFunction)

        self.customFilters.append(customFilter)

    def setupFilter(self):
        wordList = [("\"" + f + "\"") for f in self.documentTableModel.displayedKeys]
        filterCompleter = Completer(wordList, self)
        filterCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filterCompleter.setFilterMode(QtCore.Qt.MatchContains)
        filterCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.widget.filterEdit.setCompleter(filterCompleter)

        wordList = [f for f in self.documentTableModel.displayedKeys]
        distinctCompleter = Completer(wordList, self)
        distinctCompleter.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        distinctCompleter.setFilterMode(QtCore.Qt.MatchContains)
        distinctCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        #filterCompleter.activated.connect(self.insertCompletion)
        self.widget.distinctEdit.setCompleter(distinctCompleter)

        self.addCustomFilter("Has Preview", self.hasPreviewFilter)

    def hasPreviewFilter(self, document):
        try:
            previewPath = document.get('preview')
            animPattern = r'(.*)\.(#+)\.(.*)'
            animMatch = re.match(animPattern, previewPath)
            if animMatch:
                hashtagCount = len(animMatch.group(2))
                animIndexStr = ''.join(['0' for _ in range(hashtagCount)])
                firstFramePath = re.sub(animPattern, fr'\1.{animIndexStr}.\3', previewPath)
                altFirstFramePath = re.sub(animPattern, fr'\1.{animIndexStr[:-1] + "1"}.\3', previewPath)
                return os.path.exists(firstFramePath) or os.path.exists(altFirstFramePath[:-1] + '1')
                
            return os.path.exists(previewPath)
        except:
            return False

    def getFilteredDocumentsOfCollection(self, collectionName):
        for d in self.dbManager.getFilteredDocuments(collectionName, self.getItemsFilter(), distinctionText=self.widget.distinctEdit.text()):
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

    def applyCustomFilter(self, document):
        for customFilter in self.customFilters:
            if customFilter.checkbox.isChecked() and not customFilter.filterFunction(document):
                return False

        return True

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

                    if not self.applyCustomFilter(item):
                        continue

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