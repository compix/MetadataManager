from qt_extensions.DockWidget import DockWidget
from assets import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2 import QtCore
from PySide2.QtCore import QThreadPool
from MetadataManagerCore.third_party_integrations.deadline_service import DeadlineService, DeadlineServiceInfo
import os
from qt_extensions import qt_util
from PySide2.QtCore import QThreadPool

class DeadlineServiceViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Deadline Service", parentWindow, asset_manager.getUIFilePath("deadlineService.ui"))
        
        self.dbManager = None
        self.deadlineService : DeadlineService = DeadlineService(None)

        self.widget.refreshConnectionButton.clicked.connect(self.onRefreshConnectionButtonClick)

        self.deadlineService.messageUpdateEvent.subscribe(self.onDeadlineServiceMessageUpdate)

    def saveState(self, settings):
        settings.setValue("deadline_service", self.deadlineService.info.__dict__)

    def updateInfo(self, info):
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setText, "Connecting...")
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setEnabled, False)
        self.deadlineService.updateInfo(info)
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setText, "Refresh Connection")
        qt_util.runInMainThread(self.widget.refreshConnectionButton.setEnabled, True)

    def refreshDeadlineServiceInfo(self, info):
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.updateInfo, info))

    def restoreState(self, settings):
        info = DeadlineServiceInfo()
        infoDict = settings.value("deadline_service")

        if infoDict != None:
            try:
                info.__dict__ = infoDict

                self.widget.hostLineEdit.setText(str(info.webserviceHost))
                self.widget.portLineEdit.setText(str(info.webservicePort))
                self.widget.deadlineStandalonePathLineEdit.setText(str(info.deadlineStandalonePythonPackagePath))
                self.widget.deadlineInstallPathLineEdit.setText(str(info.deadlineInstallPath))

                self.refreshDeadlineServiceInfo(info)
            except Exception as e:
                print(str(e))
        else:
            self.onRefreshConnectionButtonClick()

    def onDeadlineServiceMessageUpdate(self, msg):
        self.log(msg)

    def log(self, msg):
        qt_util.runInMainThread(self.widget.logEdit.append, msg)

    def onRefreshConnectionButtonClick(self):
        host = self.widget.hostLineEdit.text()
        port = self.widget.portLineEdit.text()

        try:
            port = int(port)
        except:
            pass

        info = DeadlineServiceInfo()
        info.deadlineInstallPath = self.widget.deadlineInstallPathLineEdit.text()
        info.deadlineStandalonePythonPackagePath = self.widget.deadlineStandalonePathLineEdit.text()
        info.webserviceHost = host
        info.webservicePort = port
        self.refreshDeadlineServiceInfo(info)
