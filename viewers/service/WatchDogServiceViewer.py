from PySide2.QtWidgets import QComboBox
from qt_extensions import qt_util
from MetadataManagerCore.service.WatchDogService import WatchDogService
import asset_manager
from MetadataManagerCore.service.Service import ServiceStatus
from viewers.service.ServiceViewer import ServiceViewer
from MetadataManagerCore.service.ServiceManager import ServiceManager

class WatchDogServiceViewer(ServiceViewer):
    def __init__(self, serviceRegistry) -> None:
        super().__init__(serviceRegistry)

        self._widget = asset_manager.loadUIFile('watchdogServiceViewer.ui')
        qt_util.connectFolderSelection(self.widget, self.widget.folderEdit, self.widget.selectFolderButton)
        #self.widget.sftpGroupBox.clicked.connect(lambda checked: self.widget.sftpFrame.setEnabled(checked))

        self.setupFileHandlerComboBox(self.widget.existingFileHandlerComboBox)
        self.setupFileHandlerComboBox(self.widget.createdFileHandlerComboBox)
        self.setupFileHandlerComboBox(self.widget.modifiedFileHandlerComboBox)

    @property
    def widget(self):
        return self._widget

    def getWatchedFileExtensions(self):
        extStr : str = self.widget.watchedFileExtensionsEdit.text()
        if extStr != '':
            extList = extStr.split(',')
            extList = [ext.strip() for ext in extList]
            return extList

        return None

    def getSFTPWatchDogPollingInterval(self):
        try:
            return float(self.widget.sftpPollingIntervalEdit.text())
        except:
            return None

    def setupFileHandlerComboBox(self, cb: QComboBox):
        cb.clear()

        for handlerClassName in self.serviceRegistry.fileHandlerManager.getAllHandlerClassNames():
            cb.addItem(handlerClassName)

    def getServiceInfoDict(self, serviceClassName: str, serviceName: str, serviceDescription: str, initialStatus: ServiceStatus):
        infoDict = super().getServiceInfoDict(serviceClassName, serviceName, serviceDescription, initialStatus)

        existingFileHandlerDict = None
        if self.widget.existingFileHandlerCheckBox.isChecked():
            existingFileHandlerDict = {'class': self.widget.existingFileHandlerComboBox.currentText()}

        createdFileHandlerDict = None
        if self.widget.createdFileHandlerCheckBox.isChecked():
            createdFileHandlerDict = {'class': self.widget.createdFileHandlerComboBox.currentText()}

        modifiedFileHandlerDict = None
        if self.widget.modifiedFileHandlerCheckBox.isChecked():
            modifiedFileHandlerDict = {'class': self.widget.modifiedFileHandlerComboBox.currentText()}

        serviceDict = WatchDogService.constructDict(
            self.widget.folderEdit.text(), self.getWatchedFileExtensions(), self.widget.recursiveCheckBox.isChecked(),
            self.widget.sftpGroupBox.isChecked(), self.widget.sftpHostEdit.text(), self.widget.sftpUsernameEdit.text(),
            self.widget.sftpPasswordEdit.text(), self.getSFTPWatchDogPollingInterval(), 
            existingFileHandlerDict, createdFileHandlerDict, modifiedFileHandlerDict)
        ServiceManager.setServiceInfoDict(infoDict, serviceDict)
        return infoDict