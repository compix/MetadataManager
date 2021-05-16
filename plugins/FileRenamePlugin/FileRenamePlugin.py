from DocumentFileCopyPlugin.DocumentFileCopyAction import DocumentFileCopyAction
from FileRenamePlugin.FileRenameAction import FileRenameAction
from qt_extensions import qt_util
from DocumentTaggingPlugin.DocumentTagsFilter import DocumentTagsFilter
from MetadataManagerCore.Event import Event
from ApplicationMode import ApplicationMode
from DocumentTaggingPlugin.DocumentTaggingAction import DocumentTaggingAction
from plugin.Plugin import Plugin
import asset_manager

class FileRenamePlugin(Plugin):
    def init(self):
        action = FileRenameAction()

        self.serviceRegistry.actionManager.registerAction(action)
        action.useDefaultConfirmationEvent = False

        for collectionName in self.serviceRegistry.dbManager.getVisibleCollectionNames():
            self.serviceRegistry.actionManager.linkActionToCollection(action.id, collectionName)

        if self.appInfo.mode == ApplicationMode.GUI:
            uiFilePath = asset_manager.getPluginUIFilePath("FileRenamePlugin", "assets/dialog.ui")
            self.dialog = asset_manager.loadDialogAbsolutePath(uiFilePath)

            qt_util.connectFolderSelection(self.dialog, self.dialog.sourceFolderEdit, self.dialog.sourceFolderButton)
            qt_util.connectFolderSelection(self.dialog, self.dialog.targetFolderEdit, self.dialog.targetFolderButton)

            self.dialog.cancelButton.clicked.connect(self.dialog.reject)
            self.dialog.confirmButton.clicked.connect(self.onConfirm)

            action.confirmationEvent = Event()
            self.dialog.accepted.connect(lambda: action.confirmationEvent())
            action.requestConfirmationFunction = self.onOpenDialog
            action.retrieveArgsFunction = lambda: self.actionArgs

    def onOpenDialog(self):
        self.dialog.show()

    def onConfirm(self):
        sourceFolder = self.dialog.sourceFolderEdit.text()
        sourceBasenameRegexPattern = self.dialog.sourceBasenameRegexPatternEdit.text()
        targetFolder = self.dialog.targetFolderEdit.text()
        targetBasenamePattern = self.dialog.destinationBasenamePatternEdit.text()
        targetFolders = self.dialog.targetFoldersCheckBox.isChecked()
        recurse = self.dialog.recursiveCheckBox.isChecked()
        copy = self.dialog.copyCheckBox.isChecked()

        self.actionArgs = [sourceFolder, sourceBasenameRegexPattern, targetFolder, targetBasenamePattern, targetFolders, recurse, copy]

        self.dialog.accept()