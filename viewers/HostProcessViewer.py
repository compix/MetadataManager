from typing import Dict
from PySide2 import QtGui
from PySide2.QtWidgets import QMessageBox, QTableWidget
from qt_extensions.DockWidget import DockWidget
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore.host.HostProcessController import HostProcessController, HostProcessInfo
import re

class HostProcessViewer(DockWidget):
    def __init__(self, parentWindow, hostProcessController: HostProcessController):
        super().__init__("Host Processes", parentWindow, asset_manager.getUIFilePath("hostProcesses.ui"))
        
        self.hostProcessController = hostProcessController
        self.hostTableWidget : QTableWidget = self.widget.hostTableWidget
        self.setupHostProcessTableWidgetContextMenu()

        self.tableRowIndexToHostProcessInfo : Dict[int, HostProcessInfo] = dict()

        self.hostProcessController.onHostProcessAddedEvent.subscribe(lambda _,__: self.updateHostTable())
        self.hostProcessController.onHostProcessRemovedEvent.subscribe(lambda _,__: self.updateHostTable())
        self.widget.filterLineEdit.returnPressed.connect(self.updateHostTable)
        
        self.updateHostTable()

    def updateHostTable(self):
        self.hostTableWidget.clear()
        infos = [i for i in self.hostProcessController.hostProcessInfos.values()]

        headerLabels = ['ID', 'Hostname', 'PID']
        self.hostTableWidget.setColumnCount(len(headerLabels))
        self.hostTableWidget.setHorizontalHeaderLabels(headerLabels)

        self.tableRowIndexToHostProcessInfo = dict()

        pattern = re.compile(self.widget.filterLineEdit.text())

        filteredHostProcessInfos = list(filter(lambda i: re.search(pattern, i.hostProcessId), infos))
        self.hostTableWidget.setRowCount(len(filteredHostProcessInfos))
        
        for i in range(0, len(filteredHostProcessInfos)):
            info : HostProcessInfo = infos[i]
            self.hostTableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(str(info.hostProcessId)))
            self.hostTableWidget.setItem(i, 1, QtWidgets.QTableWidgetItem(str(info.hostname)))
            self.hostTableWidget.setItem(i, 2, QtWidgets.QTableWidgetItem(str(info.pid)))

            self.tableRowIndexToHostProcessInfo[i] = info

    def setupHostProcessTableWidgetContextMenu(self):
        self.hostProcessTableWidgetContextMenu = QtWidgets.QMenu(self.widget)

        forceCloseAction = QtWidgets.QAction('Close Application', self.widget)
        self.hostProcessTableWidgetContextMenu.addAction(forceCloseAction)

        forceCloseAction.triggered.connect(self.closeSelectedHostProcesses)

        self.hostTableWidget.customContextMenuRequested.connect(self.onHostProcessTableWidgetContextMenu)

    def closeSelectedHostProcesses(self):
        ret = QMessageBox.question(self, "Close Host Process Application", f"Are you sure you want to close the selected applications?")
        if ret == QMessageBox.Yes:
            for rowIdx in set(idx.row() for idx in self.hostTableWidget.selectedIndexes()):
                info = self.tableRowIndexToHostProcessInfo[rowIdx]

                if self.hostProcessController.thisHost.hostname == info.hostname and self.hostProcessController.thisHost.pid == info.pid:
                    QMessageBox.warning(self, 'Warning', 'You can not close your own app through the host processor.')
                    continue
                
                self.hostProcessController.closeHostProcess(info.hostname, info.pid)

    def onHostProcessTableWidgetContextMenu(self):
        self.hostProcessTableWidgetContextMenu.setEnabled(len(self.hostTableWidget.selectedIndexes()) > 0)
        self.hostProcessTableWidgetContextMenu.exec_(QtGui.QCursor.pos())