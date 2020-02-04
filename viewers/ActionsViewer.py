from qt_extensions.DockWidget import DockWidget
from assets import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2 import QtCore
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from viewers.CollectionViewer import CollectionViewer
from MetadataManagerCore.actions.ActionManager import ActionManager

class ActionsViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Actions", parentWindow, asset_manager.getUIFilePath("actions.ui"))
        
        self.dbManager = None
        self.collectionViewer : CollectionViewer = None
        self.actionManager : ActionManager = None

        self.widget.actionsLayout.setAlignment(QtCore.Qt.AlignTop)

        self.targetMap = {"Selected Items": self.executeActionOnAllSelectedDocuments, "Filtered Items": self.executeActionOnAllFilteredDocuments}
        for target in self.targetMap.keys():
            self.widget.targetComboBox.addItem(target)

        self.widget.targetComboBox.currentIndexChanged.connect(self.onTargetChanged)

    def onTargetChanged(self):
        self.refreshActionView()

    def setDatabaseManager(self, dbManager):
        self.dbManager = dbManager

    def setup(self, actionManager: ActionManager, mainWindowManager, collectionViewer: CollectionViewer):
        self.actionManager = actionManager
        self.collectionViewer = collectionViewer
        self.refreshActionView()
        self.mainWindowManager = mainWindowManager

        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.onCollectionSelectionChanged)

        self.actionManager.linkActionToCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())
        self.actionManager.unlinkActionFromCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())

    def onCollectionSelectionChanged(self):
        self.refreshActionView()

    def executeActionOnAllFilteredDocuments(self, action: DocumentAction):
        for document in self.mainWindowManager.getFilteredDocuments():
            action.execute(document)

    def refreshActionView(self):
        target = self.widget.targetComboBox.currentText()

        if self.actionManager != None:
            qt_util.clearContainer(self.widget.actionsLayout)
            
            # Only show actions that can be used for all selected collections:
            availableActionIds = set([a.id for a in self.actionManager.actions])
            selectedCollectionNames = [collectionName for collectionName in self.collectionViewer.yieldSelectedCollectionNames()]
            if len(selectedCollectionNames) == 0:
                availableActionIds = []

            for collection in selectedCollectionNames:
                availableActionIds = availableActionIds.intersection(self.actionManager.getCollectionActionIds(collection))

            for actionId in availableActionIds:
                a = self.actionManager.getActionById(actionId)
                actionButton = QtWidgets.QPushButton(a.id, self.widget)
                actionButton.clicked.connect(lambda: self.targetMap[target](a))
                self.widget.actionsLayout.addWidget(actionButton)

    def executeActionOnAllSelectedDocuments(self, action: DocumentAction):
        for uid in self.mainWindowManager.selectedDocumentIds:
            document = self.dbManager.findOne(uid)
            if document != None:
                action.execute(document)
            
