from qt_extensions.DockWidget import DockWidget
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2 import QtCore
from PySide2.QtCore import QThreadPool
from MetadataManagerCore.third_party_integrations.deadline.deadline_service import DeadlineService, DeadlineServiceInfo
import os
from qt_extensions import qt_util
from PySide2.QtCore import QThreadPool
from PySide2.QtWidgets import QMessageBox
from logging_extensions.QtTextAppendLoggingHandler import QtTextAppendLoggingHandler
import logging

class DeadlineServiceViewer(DockWidget):
    def __init__(self, parentWindow, deadlineService : DeadlineService):
        super().__init__("Deadline Service", parentWindow, asset_manager.getUIFilePath("deadlineService.ui"))
        
        self.dbManager = None
        self.deadlineService : DeadlineService = deadlineService
        self.logger = logging.getLogger(__name__)

        self.widget.refreshConnectionButton.clicked.connect(self.onRefreshConnectionButtonClick)
        self.widget.installPluginButton.clicked.connect(self.onInstallPluginClick)

        textAppendLoggingHandler = QtTextAppendLoggingHandler(self.widget.logEdit)
        self.logger.addHandler(textAppendLoggingHandler)
        self.deadlineService.logger.addHandler(textAppendLoggingHandler)

        self.availablePluginsMap = {"3ds Max Pipeline Plugin":"3dsMaxPipeline", 
                                    "Metadata Manager Plugin":"MetadataManager"}

        for key in self.availablePluginsMap.keys():
            self.widget.installPluginComboBox.addItem(key)

    def saveState(self, settings):
        pass

    def updateInfo(self, info):
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setText, "Connecting...")
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setEnabled, False)
        self.deadlineService.updateInfo(info)
        self.deadlineService.saveToDB()
        self.deadlineService.connect()
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setText, "Refresh Connection")
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setEnabled, True)

    def refreshDeadlineServiceInfo(self, info):
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.updateInfo, info))

    def onInstallPluginClick(self):
        selectedPlugin = self.widget.installPluginComboBox.currentText()
        installationSuccessful = self.deadlineService.installKnownDeadlinePlugin(self.availablePluginsMap.get(selectedPlugin))
        infoText = f"Sucessfully installed {selectedPlugin}." if installationSuccessful else f"Failed to install {selectedPlugin}. Please check the log."
        self.logger.info(infoText)

        if not installationSuccessful:
            QMessageBox.warning(self.widget, "Installation Failed", infoText)

    def restoreState(self, settings):
        if self.deadlineService.info != None:
            try:
                info = self.deadlineService.info

                self.widget.hostLineEdit.setText(str(info.webserviceHost))
                self.widget.portLineEdit.setText(str(info.webservicePort))
                self.widget.deadlineInstallPathLineEdit.setText(str(info.deadlineInstallPath))
                self.widget.deadlineRepositoryLocationLineEdit.setText(str(info.deadlineRepositoryLocation))
                
                self.refreshDeadlineServiceInfo(info)
            except Exception as e:
                print(str(e))
        else:
            self.onRefreshConnectionButtonClick()

    def onRefreshConnectionButtonClick(self):
        host = self.widget.hostLineEdit.text()
        port = self.widget.portLineEdit.text()

        try:
            port = int(port)
        except:
            pass

        info = DeadlineServiceInfo()
        info.deadlineInstallPath = self.widget.deadlineInstallPathLineEdit.text()
        info.webserviceHost = host
        info.webservicePort = port
        info.deadlineRepositoryLocation = self.widget.deadlineRepositoryLocationLineEdit.text()
        self.refreshDeadlineServiceInfo(info)