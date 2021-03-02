import PySide2
from PySide2.QtGui import QColor
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
from PySide2.QtWidgets import QCheckBox, QListWidget, QListWidgetItem, QHBoxLayout, QLineEdit, QTableWidget, QWidget, QLayout, QAbstractItemView, QVBoxLayout
from PySide2 import QtGui
from PySide2.QtCore import QThreadPool
import json
from typing import Any, Dict, List
import os
import re
from MetadataManagerCore.util import timeit
from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager

class FilteredDocumentsSnapshot(object):
    def __init__(self, documentSearchFilterViewer) -> None:
        super().__init__()

        self.fullSearchFilterInfo = documentSearchFilterViewer.getCurrentFullSearchFilterEntry()
        self.collectionNames = [cn for cn in documentSearchFilterViewer.collectionViewer.yieldSelectedCollectionNames()]
        self.documentFilterManager: DocumentFilterManager = documentSearchFilterViewer.documentFilterManager
        self.itemsFilter = documentSearchFilterViewer.getItemsFilter()
        self.documentCount = documentSearchFilterViewer.currentDocumentCount

    def yieldDocuments(self):
        distinctionText = self.fullSearchFilterInfo['distinctionText']
        customFilters = []
        for filterDict in self.fullSearchFilterInfo['customFilters']:
            f = None
            for filter_ in self.documentFilterManager.customFilters:
                if filter_.uniqueFilterLabel == filterDict['uniqueFilterLabel']:
                    f = filter_.copy()
                    f.setFromDict(filterDict)
                    break
            
            if f:
                customFilters.append(f)
            else:
                raise RuntimeError(f'Unknown filter: {filterDict["uniqueFilterLabel"]}')

        for collectionName in self.collectionNames:
            for d in self.documentFilterManager.yieldFilteredDocuments(collectionName, self.itemsFilter, distinctionText=distinctionText, filters=customFilters):
                yield d

class DocumentFilterView(object):
    def __init__(self, documentFilter : DocumentFilter):
        self.documentFilter = documentFilter

        self.activeCheckBox = QCheckBox()
        self.activeCheckBox.setChecked(documentFilter.active)
        self.activeCheckBox.stateChanged.connect(self.onActiveCheckBoxChanged)
        self.activeCheckBox.setText(self.documentFilter.uniqueFilterLabel)

        self.negateCheckBox = QCheckBox()
        self.negateCheckBox.setChecked(documentFilter.negate)
        self.negateCheckBox.stateChanged.connect(self.onNegateCheckBoxChanged)
        self.negateCheckBox.setText('Negate')

        self.container = QWidget()
        layout = QHBoxLayout()
        self.container.setLayout(layout)
        self.container.layout().addWidget(self.activeCheckBox)
        self.container.layout().addWidget(self.negateCheckBox)

        if documentFilter.hasStringArg:
            self.container.layout().addWidget(QtWidgets.QLabel("Input:"))
            self.textEdit = QLineEdit()
            self.textEdit.setText(documentFilter.args)
            self.textEdit.textChanged.connect(self.onTextEditChanged)
            self.container.layout().addWidget(self.textEdit)

        self.container.layout().setAlignment(QtCore.Qt.AlignLeft)
        self.container.adjustSize()

        self.container.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        self.container.setFixedHeight(20)

        self.currentDocumentCount = 0
    
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
        self.highlightDocumentsWithPreview = True
        self.previewHighlightCache: Dict[int,bool] = dict()

        self.appInfo = appInfo
        self.mainWindow = mainWindow
        self.dbManager = dbManager
        self.documentFilterManager = documentFilterManager
        self.documentTableModel = documentTableModel
        self.collectionViewer = collectionViewer
        self.documentFilterViews : List[DocumentFilterView] = []
        self.searchFilterQueue = []
        self.savedFilters = []
        self.savedFilterNameToActionMap = dict()
        self.historyMenu = None
        self.maxSearchFilterDisplayedCharCount = 100

        self.customFilterScrollAreaLayout : QVBoxLayout = self.widget.customFilterScrollAreaLayout
        self.customFilterScrollAreaLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.findPushButton.clicked.connect(self.viewItemsOverThreadPool)
        self.widget.filterEdit.returnPressed.connect(self.viewItemsOverThreadPool)
        self.widget.distinctEdit.returnPressed.connect(self.viewItemsOverThreadPool)

        self.setupFilter()
        self.updateDisplayedFilters()

        self.documentFilterManager.onFilterListUpdateEvent.subscribe(self.updateDisplayedFilters)

        self.setupHistoryContextMenu()

        self.widget.fullFilterApplyButton.clicked.connect(self.onFullFilterApplyButtonClicked)
        self.widget.fullFilterLineEdit.returnPressed.connect(self.onFullFilterApplyButtonClicked)
        self.widget.copyFullSearchToClipboardButton.clicked.connect(self.onCopyFullSearchToClipboardClicked)

        self.setupSavedFiltersUI()

        self.updateHighlightDocumentsWithPreviewColorFunction()
        self.mainWindow.highlightDocumentsWithPreviewCheckBox.stateChanged.connect(self.onHighlightDocumentsWithPreviewCheckBoxChanged)

    def getFilteredDocumentsSnapshot(self):
        return FilteredDocumentsSnapshot(self)

    def updateHighlightDocumentsWithPreviewColorFunction(self):
        checkBox: QCheckBox = self.mainWindow.highlightDocumentsWithPreviewCheckBox
        if checkBox.isChecked():
            self.documentTableModel.cellColorFunction = self.previewHighlightCellColorFunction
        else:
            self.documentTableModel.cellColorFunction = None

        self.documentTableModel.update()

    def onHighlightDocumentsWithPreviewCheckBoxChanged(self):
        self.updateHighlightDocumentsWithPreviewColorFunction()

    def setupSavedFiltersUI(self):
        self.widget.saveFilterButton.clicked.connect(self.onSaveFilter)

        self.widget.savedFiltersComboBox.currentTextChanged.connect(self.applySavedFilter)
        self.widget.savedFiltersComboBox.customContextMenuRequested.connect(self.onSavedFiltersComboBoxContextMenu)

        self.savedFiltersComboBoxMenu = QtWidgets.QMenu(self.widget)
        action = QtWidgets.QAction("Delete Selected", self.widget)
        self.savedFiltersComboBoxMenu.addAction(action)

        action.triggered.connect(self.onDeleteSelectedSavedFilter)

    def onDeleteSelectedSavedFilter(self):
        entryName = self.widget.savedFiltersComboBox.currentText()
        self.savedFilters = [savedFilter for savedFilter in self.savedFilters if not self.getSearchFilterEntryName(savedFilter, self.maxSearchFilterDisplayedCharCount) == entryName]
        self.updateSavedFiltersComboBox()

    def onSavedFiltersComboBoxContextMenu(self, point):
        self.savedFiltersComboBoxMenu.exec_(QtGui.QCursor.pos())

    def applySavedFilter(self, filterName):
        filterAction = self.savedFilterNameToActionMap.get(filterName)
        if filterAction:
            filterAction()

    def onSaveFilter(self):
        entry = self.getCurrentFullSearchFilterEntry()
        self.savedFilters.append(entry)
        self.updateSavedFiltersComboBox()

    def updateSavedFiltersComboBox(self):
        self.widget.savedFiltersComboBox.currentTextChanged.disconnect()
        self.widget.savedFiltersComboBox.clear()

        for searchFilterEntry in self.savedFilters:
            entryName = self.getSearchFilterEntryName(searchFilterEntry, self.maxSearchFilterDisplayedCharCount)
            self.widget.savedFiltersComboBox.addItem(entryName)

            self.savedFilterNameToActionMap[entryName] = (lambda searchFilterEntry_: lambda: self.applyFullSearchFilterEntry(searchFilterEntry_))(searchFilterEntry)

        self.widget.savedFiltersComboBox.currentTextChanged.connect(self.applySavedFilter)

    def onFullFilterApplyButtonClicked(self):
        try:
            self.applyFullSearchFilterEntry(json.loads(self.widget.fullFilterLineEdit.text()))
        except:
            QtWidgets.QMessageBox.warning(self.widget, 'Invalid Filter', 'The entered filter is not valid.')

    def onCopyFullSearchToClipboardClicked(self):
        jsonAsStr = json.dumps(self.getCurrentFullSearchFilterEntry())
        QtGui.QGuiApplication.clipboard().setText(jsonAsStr)
        
    def viewItemsOverThreadPool(self, saveSearchHistoryEntry = True):
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.viewItems, saveSearchHistoryEntry))

    def setupHistoryContextMenu(self):
        # set button context menu policy
        self.widget.historyButton.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.widget.historyButton.customContextMenuRequested.connect(self.onHistoryContextMenu)
        self.widget.historyButton.clicked.connect(self.onHistoryContextMenu)

    def onHistoryContextMenu(self):
        if self.historyMenu:
            self.historyMenu.exec_(QtGui.QCursor.pos())
        else:
             QtWidgets.QMessageBox.warning(self.widget, "Empty Search History", "The search history is empty.")

    def applyFullSearchFilterEntry(self, entry):
        self.widget.filterEdit.setText(entry['itemsFilterText'])
        self.widget.distinctEdit.setText(entry['distinctionText'])

        for filterDict in entry['customFilters']:
            for searchFilter in self.documentFilterManager.customFilters:
                if searchFilter.uniqueFilterLabel == filterDict['uniqueFilterLabel']:
                    searchFilter.setFromDict(filterDict)
                    break

        self.updateDisplayedFilters()
        self.viewItemsOverThreadPool(False)

    def getSearchFilterEntryName(self, entry: dict, maxCharacterCount: int):
        entryName = entry['itemsFilterText']
        # Add filter info:
        for filterDict in entry['customFilters']:
            if filterDict['active']:
                entryName += '; ' + filterDict['uniqueFilterLabel']
                if filterDict['hasStringArg']:
                    entryName += f'({filterDict["args"]})'

        if len(entryName) > maxCharacterCount:
            entryName = entryName[:maxCharacterCount] + "..."
        
        return entryName

    def updateSearchHistory(self):
        self.historyMenu = QtWidgets.QMenu(self.widget)

        for searchFilterEntry in self.searchFilterQueue:
            entryName = self.getSearchFilterEntryName(searchFilterEntry, self.maxSearchFilterDisplayedCharCount)

            action = QtWidgets.QAction(entryName, self.widget)
            self.historyMenu.addAction(action)

            action.triggered.connect((lambda searchFilterEntry_: lambda: self.applyFullSearchFilterEntry(searchFilterEntry_))(searchFilterEntry))

    def getCurrentFullSearchFilterEntry(self):
        customFilters = []
        for searchFilter in self.documentFilterManager.customFilters:
            customFilters.append(searchFilter.asDict())

        entry = {
            'itemsFilterText': self.widget.filterEdit.text(),
            'distinctionText': self.widget.distinctEdit.text(),
            'customFilters': customFilters
        }

        return entry

    def addCurrentSearchHistoryEntry(self):
        self.searchFilterQueue.insert(0,self.getCurrentFullSearchFilterEntry())
        if len(self.searchFilterQueue) > 10:
            self.searchFilterQueue.pop()

        self.updateSearchHistory()

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

        maxWidth = 0
        for filterView in self.documentFilterViews:
            maxWidth = max(maxWidth, filterView.activeCheckBox.width())

        for filterView in self.documentFilterViews:
            filterView.activeCheckBox.setFixedWidth(maxWidth)

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
    def viewItems(self, saveSearchHistoryEntry = True):
        if len(self.documentTableModel.displayedKeys) == 0:
            return

        self.previewHighlightCache = dict()

        qt_util.runInMainThread(self.widget.findPushButton.setEnabled, False)

        qt_util.runInMainThread(self.documentTableModel.clear)
        qt_util.runInMainThread(lambda: self.mainWindow.itemCountLabel.setText("Item Count: Computing..."))

        self.initDocumentProgress(0)

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

        self.currentDocumentCount = i
        self.initDocumentProgress(i if i > 0 else 1)
        qt_util.runInMainThread(lambda:self.mainWindow.itemCountLabel.setText("Item Count: " + str(i)))
        self.updateDocumentProgress(0.0)

        qt_util.runInMainThread(self.widget.findPushButton.setEnabled, True)
        if saveSearchHistoryEntry:
            qt_util.runInMainThread(self.addCurrentSearchHistoryEntry)

    def previewHighlightCellColorFunction(self, rowIdx: int, colIdx: int, data):
        v = self.previewHighlightCache.get(rowIdx)

        if v != None:
            return QColor.fromRgb(10,52,22) if v else None

        uid = self.documentTableModel.getUID(rowIdx)
        doc = self.dbManager.findOne(uid)
        
        if doc:
            preview = doc.get('preview')
            hasPreview = preview and os.path.exists(preview)
            self.previewHighlightCache[rowIdx] = hasPreview
            if hasPreview:
                return QColor.fromRgb(10,52,22)

        return None

    def saveState(self, settings: QtCore.QSettings):
        settings.setValue("searchFilterQueue", self.searchFilterQueue)
        settings.setValue("savedSearchFilters", self.savedFilters)

    def restoreState(self, settings: QtCore.QSettings):
        try:
            self.searchFilterQueue = settings.value("searchFilterQueue")
            self.updateSearchHistory()
        except:
            pass

        try:
            self.savedFilters = settings.value("savedSearchFilters")
            self.updateSavedFiltersComboBox()
        except:
            pass

        if not self.savedFilters:
            self.savedFilters = []

        if not self.searchFilterQueue:
            self.searchFilterQueue = []