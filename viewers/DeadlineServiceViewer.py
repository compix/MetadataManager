from qt_extensions.DockWidget import DockWidget
from assets import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2 import QtCore
from PySide2.QtCore import QThreadPool
from MetadataManagerCore.third_party_integrations.deadline_service import DeadlineService, DeadlineServiceInfo
import os

class DeadlineServiceViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Deadline Service", parentWindow, asset_manager.getUIFilePath("deadlineService.ui"))
        
        self.dbManager = None
        self.deadlineService : DeadlineService = DeadlineService(None)

        self.widget.refreshConnectionButton.clicked.connect(self.onRefreshConnectionButtonClick)

        self.deadlineService.messageUpdateEvent.subscribe(self.onDeadlineServiceMessageUpdate)

        self.onRefreshConnectionButtonClick()

    def onDeadlineServiceMessageUpdate(self, msg):
        self.log(msg)

    def log(self, msg):
        self.widget.logEdit.append(msg)

    def onRefreshConnectionButtonClick(self):
        host = self.widget.hostLineEdit.text()
        port = self.widget.portLineEdit.text()

        try:
            port = int(port)
        except:
            pass

        info = DeadlineServiceInfo()
        info.deadlineCmdPath = os.path.join(self.widget.deadlineInstallPathLineEdit.text(), r"bin\deadlinecommand.exe")
        info.deadlineStandalonePythonPackagePath = self.widget.deadlineStandalonePathLineEdit.text()
        info.webserviceHost = host
        info.webservicePort = port
        self.deadlineService.updateInfo(info)