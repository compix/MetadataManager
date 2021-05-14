from DocumentFileCopyPlugin.DocumentFileCopyAction import DocumentFileCopyAction
from qt_extensions import qt_util
from DocumentTaggingPlugin.DocumentTagsFilter import DocumentTagsFilter
from MetadataManagerCore.Event import Event
from ApplicationMode import ApplicationMode
from DocumentTaggingPlugin.DocumentTaggingAction import DocumentTaggingAction
from plugin.Plugin import Plugin
import asset_manager

class DocumentFileCopyPlugin(Plugin):
    def init(self):
        copyAction = DocumentFileCopyAction()

        self.serviceRegistry.actionManager.registerAction(copyAction)

        for collectionName in self.serviceRegistry.dbManager.getVisibleCollectionNames():
            self.serviceRegistry.actionManager.linkActionToCollection(copyAction.id, collectionName)

        if self.appInfo.mode == ApplicationMode.GUI:
            uiFilePath = asset_manager.getPluginUIFilePath("DocumentFileCopyPlugin", "assets/fileCopyDialog.ui")
            self.dialog = asset_manager.loadDialogAbsolutePath(uiFilePath)

            qt_util.connectFolderSelection(self.dialog, self.dialog.destinationFolderEdit, self.dialog.destinationFolderButton)

            self.dialog.cancelButton.clicked.connect(self.dialog.reject)
            self.dialog.confirmButton.clicked.connect(self.onConfirm)

            copyAction.confirmationEvent = Event()
            self.dialog.accepted.connect(lambda: copyAction.confirmationEvent())
            copyAction.requestConfirmationFunction = self.onOpenDialog
            copyAction.retrieveArgsFunction = lambda: self.actionArgs

    def onOpenDialog(self):
        self.dialog.show()

    def onConfirm(self):
        documentFileKey = self.dialog.documentFileKeyEdit.text()
        targetFolder = self.dialog.destinationFolderEdit.text()
        extendHashtagToAnimationFrames = self.dialog.extendHashtagToAnimationFramesCheckBox.isChecked()

        if self.dialog.renameGroupBox.isChecked():
            self.actionArgs = [documentFileKey, targetFolder, extendHashtagToAnimationFrames, True,
                               self.dialog.sourceFilenameRegexPatternEdit.text(), self.dialog.targetFilenamePatternEdit.text()]
        else:
            self.actionArgs = [documentFileKey, targetFolder, extendHashtagToAnimationFrames]

        self.dialog.accept()