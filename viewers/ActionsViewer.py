from qt_extensions.ProgressDialog import ProgressDialog
from typing import Any
from PySide2.QtWidgets import QProgressBar, QStatusBar
from viewers.DocumentSearchFilterViewer import DocumentSearchFilterViewer
from MetadataManagerCore.actions.ActionType import ActionType
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
from VisualScripting.VisualScriptingViewer import VisualScriptingViewer
from MetadataManagerCore.mongodb_manager import MongoDBManager
import logging

logger = logging.getLogger(__name__)

class FuncWrapper:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self) -> Any:
        return self.func(*self.args, **self.kwargs)

class ActionButtonTask(object):
    def __init__(self, action: Action, func, *args, **kwargs):
        self.action = action
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.runsOnMainThread = False

        self.confirmationFunc = None

    def setConfirmationFunction(self, confirmationFunc, *args, **kwargs):
        self.confirmationFunc = FuncWrapper(confirmationFunc, *args, **kwargs)
        
    def __call__(self):
        confirmed = True
        if self.action.useDefaultConfirmationEvent:
            confirmed = self.confirmationFunc == None or self.confirmationFunc()

        if confirmed:            
            if self.action.confirmationEvent != None and self.action.requestConfirmationFunction != None:
                self.action.confirmationEvent.clear()
                self.action.confirmationEvent.subscribe(self.onConfirmation)
                self.action.requestConfirmationFunction()
            else:
                self.onConfirmation()

    def onConfirmation(self):
        actionArgs = self.action.retrieveArgsFunction() if self.action.retrieveArgsFunction else []

        if self.runsOnMainThread:
            self.func(*self.args, *actionArgs, **self.kwargs)
        else:
            QThreadPool.globalInstance().start(qt_util.LambdaTask(self.func, *self.args, *actionArgs, **self.kwargs))

def clearContainer(container):
    for i in reversed(range(container.count())): 
        container.itemAt(i).widget().setParent(None)


class ActionsViewer(DockWidget):
    def __init__(self, parentWindow, dbManager : MongoDBManager, actionManager: ActionManager, 
                 mainWindowManager, collectionViewer: CollectionViewer, visualScriptingViewer: VisualScriptingViewer):
        super().__init__("Actions", parentWindow, asset_manager.getUIFilePath("actions.ui"))
        
        self.dbManager = dbManager
        self.collectionViewer : CollectionViewer = collectionViewer
        self.actionManager : ActionManager = actionManager
        self.visualScriptingViewer : VisualScriptingViewer = visualScriptingViewer
        self.mainWindowManager = mainWindowManager
        self.statusBar: QStatusBar = mainWindowManager.window.statusBar()

        self.widget.documentActionsLayout.setAlignment(QtCore.Qt.AlignTop)
        self.widget.generalActionsLayout.setAlignment(QtCore.Qt.AlignTop)

        self.targetMap = {"Selected Items": self.executeActionOnAllSelectedDocuments, 
                          "Filtered Items": self.executeActionOnAllFilteredDocuments}

        self.confirmationFunctionMap = {"Selected Items": self.documentActionConfirmationForSelectedItems, 
                                        "Filtered Items": self.documentActionConfirmationForFilteredItems}

        for target in self.targetMap.keys():
            self.widget.targetComboBox.addItem(target)

        self.widget.targetComboBox.currentIndexChanged.connect(self.onTargetChanged)

        self.actionTasks = []
        
        self.actionProgressUpdateEventSubscriptions = []
        self.refreshActionView()

        self.collectionViewer.connectCollectionSelectionUpdateHandler(self.onCollectionSelectionChanged)

        self.actionManager.linkActionToCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())
        self.actionManager.unlinkActionFromCollectionEvent.subscribe(lambda actionId, collectionName: self.refreshActionView())
        self.actionManager.registerActionEvent.subscribe(lambda action: self.refreshActionView())
        self.visualScriptingViewer.onSaveEvent.subscribe(self.onVisualScriptingSave)

        self.progressDialog: ProgressDialog = None
        self.setupProgressDialog()

    def onTargetChanged(self):
        self.refreshActionView()

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
            
            # Clear previous action update event subscriptions
            for action, onActionProgressUpdate in self.actionProgressUpdateEventSubscriptions:
                if action.actionType != ActionType.DocumentAction:
                    action.progressUpdateEvent.unsubscribe(onActionProgressUpdate)

            # Subscribe to action progress updates
            self.actionProgressUpdateEventSubscriptions = []
            for action in self.actionManager.actions:
                if action.actionType != ActionType.DocumentAction:
                    self.actionProgressUpdateEventSubscriptions.append((action, self.onActionProgressUpdate))
                    action.progressUpdateEvent.subscribe(self.onActionProgressUpdate)

            # Only show actions that can be used for all selected collections:
            availableActionIds = set([a.id for a in self.actionManager.actions])
            selectedCollectionNames = [collectionName for collectionName in self.collectionViewer.yieldSelectedCollectionNames()]
            if len(selectedCollectionNames) == 0:
                availableActionIds = []

            for collection in selectedCollectionNames:
                availableActionIds = availableActionIds.intersection(self.actionManager.getCollectionActionIds(collection))

            for actionId in sorted(availableActionIds):
                a = self.actionManager.getActionById(actionId)
                actionButton = QtWidgets.QPushButton(a.displayName, self.widget)

                if a.actionType == ActionType.DocumentAction:
                    task = ActionButtonTask(a, self.executeDocumentAction, target, a)
                    task.setConfirmationFunction(self.confirmationFunctionMap[target], a)
                    self.widget.documentActionsLayout.addWidget(actionButton)
                else:
                    task = ActionButtonTask(a, self.executeAction, a)
                    task.setConfirmationFunction(self.generalActionConfirmation, a)
                    self.widget.generalActionsLayout.addWidget(actionButton)

                task.runsOnMainThread = a.runsOnMainThread
                self.actionTasks.append(task)
                actionButton.clicked.connect(task)

    def onActionProgressUpdate(self, action: Action, progress: float, progressMessage: str):
        if action.runsOnMainThread:
            self.progressDialog.updateProgress(progress, progressMessage)
        else:
            self.updateProgressAsync(action, progress, progressMessage)

    def documentActionConfirmationForFilteredItems(self, action: DocumentAction):
        count = self.mainWindowManager.documentSearchFilterViewer.currentDocumentCount
        ret = QtWidgets.QMessageBox.question(self.parentWindow, f"Action Execution Confirmation", f"Execute \"{action.displayName}\" for {count} <b>filtered</b> documents?")
        return ret == QtWidgets.QMessageBox.Yes

    def documentActionConfirmationForSelectedItems(self, action: DocumentAction):
        count = len([i for i in self.mainWindowManager.selectedDocumentIds])
        if count > 0:
            ret = QtWidgets.QMessageBox.question(self.parentWindow, f"Action Execution Confirmation", f"Execute \"{action.displayName}\" for {count} selected documents?")
            return ret == QtWidgets.QMessageBox.Yes
        else:
            QtWidgets.QMessageBox.warning(self.parentWindow, "Empty Selection", "Please select documents to execute actions.")
            return False

    def setupProgressDialog(self):
        self.progressDialog = ProgressDialog()

    def executeAction(self, action : Action, *actionArgs):
        if action.runsOnMainThread:
            self.progressDialog.setTitle(action.displayName)
            self.progressDialog.open()

        action.execute(*actionArgs)

        if action.runsOnMainThread:
            self.progressDialog.close()
        else:
            self.clearProgressAsync()

    def generalActionConfirmation(self, action: Action):
        ret = QtWidgets.QMessageBox.question(self.parentWindow, f"Action Execution Confirmation", f"Execute \"{action.displayName}\"?")
        return ret == QtWidgets.QMessageBox.Yes

    def executeDocumentAction(self, target, action : DocumentAction, *actionArgs):
        self.targetMap[target](action, *actionArgs)

    def executeActionOnAllFilteredDocuments(self, action: DocumentAction, *actionArgs):
        documentSearchFilterViewer : DocumentSearchFilterViewer = self.mainWindowManager.documentSearchFilterViewer
        snapshot = documentSearchFilterViewer.getFilteredDocumentsSnapshot()
        documentCount = snapshot.documentCount
        i = 0

        for document in snapshot.yieldDocuments():
            action.execute(document, *actionArgs)

            self.updateProgressAsync(action, float(i+1) / documentCount, action.currentProgressMessage)
            i += 1

        self.clearProgressAsync()

    def executeActionOnAllSelectedDocuments(self, action: DocumentAction, *actionArgs):
        selectedDocumentIds = [i for i in self.mainWindowManager.selectedDocumentIds]
        selectedDocumentCount = len(selectedDocumentIds)

        for i, uid in enumerate(selectedDocumentIds):
            document = self.dbManager.findOne(uid)
            if document != None:
                action.execute(document, *actionArgs)
            else:
                logger.warning(f'Could not find document with id {uid}')

            self.updateProgressAsync(action, float(i+1) / selectedDocumentCount, action.currentProgressMessage)

        self.clearProgressAsync()

    def clearProgressAsync(self):
        qt_util.runInMainThread(self.statusBar.showMessage, '')
            
    def updateProgressAsync(self, action: Action, progress: float, progressMessage: str = None):
        progressStr = str(int(progress * 100))
        if progressMessage == None:
            progressMessage = 'Executing...'

        msg = f'{action.displayName}: {progressMessage} ({progressStr}%)'
        qt_util.runInMainThread(self.statusBar.showMessage, msg)
