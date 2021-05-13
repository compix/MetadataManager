from MetadataManagerCore.Event import Event
from ApplicationMode import ApplicationMode
from PySide2 import QtWidgets
from DocumentTaggingPlugin.DocumentTaggingAction import DocumentTaggingAction
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager
from RenderingPipelinePlugin.RenderingPipelineViewer import RenderingPipelineViewer
from plugin.Plugin import Plugin
import asset_manager

class DocumentTaggingPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__()

    def init(self):
        self.renderingPipelineManager = RenderingPipelineManager(self.serviceRegistry, self.viewerRegistry, self.appInfo)

        if self.appInfo.mode == ApplicationMode.GUI:
            taggingAction = DocumentTaggingAction(self.serviceRegistry.dbManager)

            uiFilePath = asset_manager.getPluginUIFilePath("DocumentTaggingPlugin", "assets/inputDialog.ui")
            self.taggingDialog = asset_manager.loadDialogAbsolutePath(uiFilePath)

            self.taggingDialog.cancelButton.clicked.connect(self.taggingDialog.reject)
            self.taggingDialog.confirmButton.clicked.connect(self.onConfirm)

            taggingAction.confirmationEvent = Event()
            self.taggingDialog.accepted.connect(lambda: taggingAction.confirmationEvent())
            taggingAction.requestConfirmationFunction = self.onOpenTaggingDialog
            taggingAction.retrieveArgsFunction = lambda: self.taggingActionArgs

            self.serviceRegistry.actionManager.registerAction(taggingAction)

            for collectionName in self.serviceRegistry.dbManager.getVisibleCollectionNames():
                self.serviceRegistry.actionManager.linkActionToCollection(taggingAction.id, collectionName)

    def onOpenTaggingDialog(self):
        self.taggingDialog.show()

    def onConfirm(self):
        tagsStr = self.taggingDialog.tagEdit.text()
        if not tagsStr:
            self.taggingDialog.reject()
            return

        tags = [t.strip() for t in tagsStr.split(',')]
        tags = [t for t in tags if t]

        if len(tags) == 0:
            self.taggingDialog.reject()
            return

        self.taggingActionArgs = [tags, self.taggingDialog.replaceExistingTagsCheckBox.isChecked()]
        self.taggingDialog.accept()