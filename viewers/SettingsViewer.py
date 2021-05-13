from PySide2.QtWidgets import QMessageBox
from qt_extensions.DockWidget import DockWidget
import asset_manager
from ServiceRegistry import ServiceRegistry
from MetadataManagerCore import Keys
from qt_extensions.ProgressDialog import ProgressDialog

class SettingsViewer(DockWidget):
    def __init__(self, parentWindow, serviceRegistry: ServiceRegistry):
        super().__init__("Settings", parentWindow, asset_manager.getUIFilePath("settings.ui"))

        self.serviceRegistry = serviceRegistry

        self.widget.updateDocumentsButton.clicked.connect(self.onUpdateDocuments)

    def onUpdateDocuments(self):
        # Confirmation dialog:
        ret = QMessageBox.question(self.widget, 'Document Update Confirmation', 'Are you sure you want to update all documents? This may take a while.')
        if ret != QMessageBox.Yes:
            return

        dbManager = self.serviceRegistry.dbManager
        progressDialog = ProgressDialog()
        progressDialog.open()

        progressDialog.updateProgress(0, 'Preparing...')
        totalCount = 0
        for collectionName in dbManager.getVisibleCollectionNames():
            collection = dbManager.db[collectionName]

            totalCount += collection.count_documents({})

        progressDialog.updateProgress(0, 'Updating documents...')
        docIdx = 0
        for collectionName in dbManager.getVisibleCollectionNames():
            collection = dbManager.db[collectionName]

            for doc in collection.find({}):
                sid = doc.get(Keys.systemIDKey)
                if sid:
                    dbManager.insertOrModifyDocument(collectionName, sid, doc, False)

                docIdx += 1

                # Progress:
                progress = float(docIdx) / totalCount
                progressDialog.updateProgress(progress)

        progressDialog.close()