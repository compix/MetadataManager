from qt_extensions.DockWidget import DockWidget
from MetadataManagerCore.actions.ActionManager import ActionManager
from PySide2.QtGui import QStandardItemModel, QStandardItem
from PySide2.QtWidgets import QListView, QAbstractItemView, QSizePolicy
from assets import asset_manager
from qt_extensions import qt_util
from MetadataManagerCore.mongodb_manager import MongoDBManager
from PySide2.QtCore import Qt
from PySide2 import QtCore

class CollectionActionListView(QListView):
    def __init__(self, parent, actionManagerViewer):
        super().__init__(parent)

        self.actionManagerViewer = actionManagerViewer
        self.setDropIndicatorShown(False)

    def getItemFromEvent(self, e):
        if e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            data = e.mimeData()
            sourceItem = QStandardItemModel()
            sourceItem.dropMimeData(data, QtCore.Qt.CopyAction, 0,0, QtCore.QModelIndex())
            return sourceItem
        
        return None

    def dragEnterEvent(self, e):
        item = None
        if e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            data = e.mimeData()
            sourceItem = QStandardItemModel()
            sourceItem.dropMimeData(data, QtCore.Qt.CopyAction, 0,0, QtCore.QModelIndex())
            item = sourceItem.item(0, 0)

        if item:
            itemName = item.text()
            currentCollection = self.actionManagerViewer.selectedCollectionName
                
            if not self.actionManagerViewer.actionManager.isValidActionId(itemName) or \
                   self.actionManagerViewer.actionManager.isActionRegisteredForCollection(itemName, currentCollection):
                e.ignore()
                return

        super().dragEnterEvent(e)

    def dropEvent(self, e):
        item = None
        if e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
            data = e.mimeData()
            sourceItem = QStandardItemModel()
            sourceItem.dropMimeData(data, QtCore.Qt.CopyAction, 0,0, QtCore.QModelIndex())
            item = sourceItem.item(0, 0)

        if item:
            itemName = item.text()

            currentCollection = self.actionManagerViewer.selectedCollectionName
            collectionActionIds = self.actionManagerViewer.actionManager.getCollectionActionIds(currentCollection)

            if item.hasChildren():
                # Add the children:
                for childActionId in self.actionManagerViewer.actionManager.getActionIdsOfCategory(itemName):
                    if self.actionManagerViewer.actionManager.isValidActionId(childActionId) and not childActionId in collectionActionIds:
                        self.actionManagerViewer.addCollectionActionEntry(childActionId)
                        self.actionManagerViewer.actionManager.linkActionToCollection(childActionId, currentCollection)
            else:
                self.actionManagerViewer.actionManager.linkActionToCollection(itemName, currentCollection)
                super().dropEvent(e)

class ActionManagerViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Actions Manager", parentWindow, asset_manager.getUIFilePath("actionManager.ui"))

        self.actionManager = None
        self.dbManager : MongoDBManager = None

        # Setup the tree view:
        self.actionsTreeView = self.widget.actionsTreeView
        self.actionsTreeModel = QStandardItemModel(self.widget)
        self.actionsTreeView.setModel(self.actionsTreeModel)

        self.widget.collectionActionsListView = CollectionActionListView(self.widget.scrollArea, self)
        self.collectionActionsListView = self.widget.collectionActionsListView

        self.collectionActionsListView.setDragEnabled(True)
        self.collectionActionsListView.setDragDropMode(QAbstractItemView.DropOnly)
        self.collectionActionsListView.setMaximumSize(100000,100000)
        self.collectionActionsListView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.collectionActionsListModel = QStandardItemModel(self.widget)
        self.collectionActionsListView.setModel(self.collectionActionsListModel)

        self.widget.collectionComboBox.currentIndexChanged.connect(self.onCollectionSelectionChanged)

        self.widget.deleteCollectionActionButton.clicked.connect(self.onDeleteCollectionActionButtonClick)

    @property
    def selectedCollectionName(self):
        return self.widget.collectionComboBox.currentText()

    def onDeleteCollectionActionButtonClick(self):
        selectionModel = self.collectionActionsListView.selectionModel()

        for rowIdx in selectionModel.selectedRows():
            listItem = self.collectionActionsListModel.item(rowIdx.row())
            actionId = listItem.text()

            self.collectionActionsListModel.removeRow(listItem.row())
            self.actionManager.unlinkActionFromCollection(actionId, self.selectedCollectionName)

    def setActionManager(self, actionManager: ActionManager):
        self.actionManager = actionManager

        self.refreshTreeView()
        self.refreshCollectionView()

        self.actionManager.registerActionEvent.subscribe(lambda action: self.refreshTreeView())

    def setDataBaseManager(self, dbManager: MongoDBManager):
        self.dbManager = dbManager

    def refreshTreeView(self):
        self.actionsTreeModel.clear()

        if self.actionManager != None:
            # First create the category items:
            categories = self.actionManager.getAllCategories()
            categoryMap = dict()
            for category in categories:
                treeItem = QStandardItem(category)
                treeItem.setDropEnabled(False)
                categoryMap[category] = treeItem

                self.actionsTreeModel.appendRow(treeItem)

            for a in self.actionManager.actions:
                categoryTreeItem = categoryMap[a.category]

                treeItem = QStandardItem(a.id)
                treeItem.setDropEnabled(False)
                categoryTreeItem.appendRow(treeItem)

    def refreshCollectionView(self):
        collectionComboBox = self.widget.collectionComboBox
        collectionComboBox.clear()

        for collectionName in self.dbManager.getCollectionNames():
            collectionComboBox.addItem(collectionName)

    def addCollectionActionEntry(self, actionId):
        item = QStandardItem(actionId)
        item.setDropEnabled(False)
        self.collectionActionsListModel.appendRow(item)

    def onCollectionSelectionChanged(self):
        currentCollection = self.widget.collectionComboBox.currentText()

        self.collectionActionsListModel.clear()
        collectionActionIds = self.actionManager.getCollectionActionIds(currentCollection)

        if collectionActionIds != None:
            for actionId in collectionActionIds:
                self.addCollectionActionEntry(actionId)

        