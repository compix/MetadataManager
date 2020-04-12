from qt_extensions.DockWidget import DockWidget
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2 import QtCore
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore.actions.Action import Action
from viewers.CollectionViewer import CollectionViewer
from MetadataManagerCore.actions.ActionManager import ActionManager
from PySide2.QtCore import QThreadPool
from VisualScripting import VisualScripting

class ActionButtonTask(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.runsOnMainThread = False

    def __call__(self):
        if self.runsOnMainThread:
            self.func(*self.args, **self.kwargs)
        else:
            QThreadPool.globalInstance().start(qt_util.LambdaTask(self.func, *self.args, **self.kwargs))
        
def clearContainer(container):
    for i in reversed(range(container.count())): 
        container.itemAt(i).widget().setParent(None)


class ActionsViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Actions", parentWindow, asset_manager.getUIFilePath("actions.ui"))
        
        self.dbManager = None
        self.collectionViewer : CollectionViewer = None
        self.actionManager : ActionManager = None
        self.visualScripting : VisualScripting = None

        self.widget.documentActionsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.generalActionsLayout.setAlignment(QtCore.Qt.AlignTop)

        self.targetMap = {"Selected Items": self.executeActionOnAllSelectedDocuments, 
                          "Filtered Items": self.executeActionOnAllFilteredDocuments}
        for target in self.targetMap.keys():
            self.widget.targetComboBox.addItem(target)

        self.widget.targetComboBox.currentIndexChanged.connect(self.onTargetChanged)

        self.actionTasks = []

    def onTargetChanged(self):
        self.refreshActionView()

    def setDatabaseManager(self, dbManager):
        self.dbManager = dbManager

    def setup(self, actionManager: ActionManager, mainWindowManager, collectionViewer: CollectionViewer, visualScripting: VisualScripting):
        self.actionManager = actionManager
        self.collectionViewer = collectionViewer
        self.refreshActionView()
        self.mainWindowManager = mainWindowManager
        self.visualScripting = visualScripting

        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.onCollectionSelectionChanged)

        self.actionManager.linkActionToCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())
        self.actionManager.unlinkActionFromCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())
        self.visualScripting.onSaveEvent.subscribe(self.onVisualScriptingSave)

    def onVisualScriptingSave(self):
        self.refreshActionView()

    def onCollectionSelectionChanged(self):
        self.refreshActionView()

    def refreshActionView(self):
        target = self.widget.targetComboBox.currentText()

        if self.actionManager != None:
            qt_util.clearContainer(self.widget.documentActionsLayout)
            qt_util.clearContainer(self.widget.generalActionsLayout)
            self.actionTasks = []

            # Only show actions that can be used for all selected collections:
            availableActionIds = set([a.id for a in self.actionManager.actions])
            selectedCollectionNames = [collectionName for collectionName in self.collectionViewer.yieldSelectedCollectionNames()]
            if len(selectedCollectionNames) == 0:
                availableActionIds = []

            for collection in selectedCollectionNames:
                availableActionIds = availableActionIds.intersection(self.actionManager.getCollectionActionIds(collection))

            for actionId in availableActionIds:
                a = self.actionManager.getActionById(actionId)
                actionButton = QtWidgets.QPushButton(a.displayName, self.widget)
                task = ActionButtonTask(self.executeDocumentAction, target, a)
                task.runsOnMainThread = a.runsOnMainThread
                self.actionTasks.append(task)
                actionButton.clicked.connect(task)
                self.widget.documentActionsLayout.addWidget(actionButton)

            # Show general actions:
            for a in self.actionManager.getGeneralActions():
                actionButton = QtWidgets.QPushButton(a.displayName, self.widget)
                task = ActionButtonTask(self.executeAction, a)
                task.runsOnMainThread = a.runsOnMainThread
                self.actionTasks.append(task)
                actionButton.clicked.connect(task)
                self.widget.generalActionsLayout.addWidget(actionButton)

    def executeAction(self, action : Action):
        action.execute()

    def executeDocumentAction(self, target, action : DocumentAction):
        self.targetMap[target](action)

    def executeActionOnAllFilteredDocuments(self, action: DocumentAction):
        for document in self.mainWindowManager.getFilteredDocuments():
            action.execute(document)

    def executeActionOnAllSelectedDocuments(self, action: DocumentAction):
        for uid in self.mainWindowManager.selectedDocumentIds:
            document = self.dbManager.findOne(uid)
            if document != None:
                action.execute(document)
            
