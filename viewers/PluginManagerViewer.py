from PySide2.QtGui import QStandardItem, QStandardItemModel
from plugin.PluginManager import PluginManager
from qt_extensions.DockWidget import DockWidget
import asset_manager
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
import qt_util

class PluginManagerViewer(DockWidget):
    def __init__(self, parentWindow: QtWidgets.QWidget, pluginManager: PluginManager, requestRestartFunction):
        super().__init__("Plugin Manager", parentWindow, asset_manager.getUIFilePath("pluginManager.ui"))
        
        self.pluginManager = pluginManager
        self.pluginTableWidget: QtWidgets.QTableWidget = self.widget.pluginTableWidget
        self.widget.statusLabel.setText('')
        self.pluginsFilter = ''
        self.shownPluginNames = []

        self.requestRestartFunction = requestRestartFunction
        self.widget.restartApplicationButton.setVisible(False)
        self.widget.restartApplicationButton.clicked.connect(self.onApplicationRestartRequest)
        self.pluginsFoldersListView: QtWidgets.QListView = self.widget.pluginsFoldersListView
        self.pluginsFoldersListView.setModel(QStandardItemModel())
        
        self.setupPluginList()

        self.pluginManager.onPluginAdded.subscribe(self.onPluginAdded)
        self.pluginManager.onPluginRemoved.subscribe(self.onPluginRemoved)

        qt_util.connectFolderSelection(parentWindow, self.widget.pluginsFolderEdit, self.widget.pathSelectButton)
        self.widget.addFolderButton.clicked.connect(self.onAddNewPluginsFolderClick)
        self.widget.deleteFolderButton.clicked.connect(self.onDeleteSelectedPluginsFolderClick)

        self.widget.pluginsFilterEdit.textChanged.connect(self.onPluginsFilterEditChanged)
        self.widget.refreshPluginsButton.clicked.connect(self.onRefreshPluginsClick)

    def onPluginAdded(self, pluginName: str):
        self.refreshPluginsTable()

    def onPluginRemoved(self, pluginName: str):
        self.refreshPluginsTable()

    def onPluginsFilterEditChanged(self, txt: str):
        self.pluginsFilter = self.widget.pluginsFilterEdit.text()
        self.refreshPluginsTable()

    def onRefreshPluginsClick(self):
        self.pluginManager.refreshAvailablePlugins()
        self.refreshPluginsTable()

    def onAddNewPluginsFolderClick(self):
        folder = self.widget.pluginsFolderEdit.text()
        try:
            if self.pluginManager.addPluginsFolder(folder):
                self.pluginsFoldersListView.model().appendRow(QStandardItem(folder))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.widget, "Warning", f'Failed to add folder. Reason: {str(e)}')
            return

        self.pluginManager.refreshPluginState()

    def onDeleteSelectedPluginsFolderClick(self):
        model: QStandardItemModel = self.pluginsFoldersListView.model()

        try:
            selectionModel = self.pluginsFoldersListView.selectionModel()
            if len(selectionModel.selectedRows()) > 0:
                if QtWidgets.QMessageBox.question(self.widget, "Confirmation", "Are you sure you want to delete the selected folders?") != QtWidgets.QMessageBox.Yes:
                    return

            for rowIdx in selectionModel.selectedRows():
                idx = rowIdx.row()
                folder = model.item(idx).text()
                self.pluginManager.removePluginsFolder(folder)
                self.pluginsFoldersListView.model().removeRow(idx)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.widget, "Warning", f'Failed to delete folder. Reason: {str(e)}')

    def loadPluginsFolders(self):
        pluginsFolders = self.pluginManager.getNonDefaultPluginsFolders()
        model: QStandardItemModel = self.pluginsFoldersListView.model()

        for folder in pluginsFolders:
            model.appendRow(QStandardItem(folder))

    def onApplicationRestartRequest(self):
        self.requestRestartFunction()

    def onPluginAutoactivateStatusChanged(self, pluginName: str, autoactivate: bool):
        checkbox = self.autoactivatePluginCheckBoxDict.get(pluginName)
        if checkbox:
            checkbox.setChecked(autoactivate)

    def wrapInHBox(self, widget: QtWidgets.QWidget):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(widget)
        layoutWidget = QtWidgets.QWidget()
        layoutWidget.setLayout(layout)
        return layoutWidget
        
    def setupPluginList(self):
        header = ['Name', 'Active', 'Auto Activate', 'Info']
        self.pluginTableWidget.setColumnCount(len(header))
        self.pluginTableWidget.setHorizontalHeaderLabels(header)
        self.autoactivatePluginCheckBoxDict = dict()

        self.refreshPluginsTable()

        self.pluginManager.onPluginAutoactivateStatusChanged.subscribe(self.onPluginAutoactivateStatusChanged)

    def refreshPluginsTable(self):
        self.pluginTableWidget.clearContents()

        self.shownPluginNames = [pluginName for pluginName in self.pluginManager.availablePluginNames if self.pluginsFilter in pluginName]
        
        rowCount = len(self.shownPluginNames)
        self.pluginTableWidget.setRowCount(rowCount)
        
        for rowIdx, pluginName in enumerate(self.shownPluginNames):
            pluginInfo = self.pluginManager.pluginInfoMap.get(pluginName)

            activeCheckbox = QtWidgets.QCheckBox()
            activeCheckbox.setChecked(pluginInfo.pluginActive)
            onActiveStatusChanged = lambda checkbox: lambda pluginActive: checkbox.setChecked(pluginActive)
            pluginInfo.onActiveStatusChanged.clear()
            pluginInfo.onActiveStatusChanged.subscribe(onActiveStatusChanged(activeCheckbox))

            autoActivateCheckbox = QtWidgets.QCheckBox()
            autoActivateCheckbox.setChecked(self.pluginManager.getPluginAutoactivateState(pluginName))
            self.autoactivatePluginCheckBoxDict[pluginName] = autoActivateCheckbox

            infoLabel = QtWidgets.QLabel()
            infoLabel.setText('')
            infoLabel.setStyleSheet("color: red") 
            
            self.pluginTableWidget.setCellWidget(rowIdx, 0, self.wrapInHBox(QtWidgets.QLabel(pluginName)))
            self.pluginTableWidget.setCellWidget(rowIdx, 1, self.wrapInHBox(activeCheckbox))
            self.pluginTableWidget.setCellWidget(rowIdx, 2, self.wrapInHBox(autoActivateCheckbox))
            self.pluginTableWidget.setCellWidget(rowIdx, 3, self.wrapInHBox(infoLabel))

            activeCheckbox.stateChanged.connect(PluginCheckboxStateChangeHandler(pluginName, self, activeCheckbox, infoLabel))
            autoActivateCheckboxChanged = lambda pluginName, checkbox: lambda: self.pluginManager.setPluginAutoactivateState(pluginName, checkbox.isChecked())
            autoActivateCheckbox.stateChanged.connect(autoActivateCheckboxChanged(pluginName, autoActivateCheckbox))

class PluginCheckboxStateChangeHandler(object):
    def __init__(self, pluginName: str, pluginManagerViewer: PluginManagerViewer, pluginCheckBox: QtWidgets.QCheckBox, infoLabel: QtWidgets.QLabel) -> None:
        super().__init__()

        self.pluginManagerViewer = pluginManagerViewer
        self.pluginManager = self.pluginManagerViewer.pluginManager
        self.checkBox = pluginCheckBox
        self.infoLabel = infoLabel
        self.pluginName = pluginName

    def __call__(self, changed):
        pluginName = self.pluginName
        pluginInfo = self.pluginManager.pluginInfoMap.get(pluginName)

        if not self.checkBox.isChecked() and pluginInfo and pluginInfo.pluginLoadingError:
            return

        self.pluginManager.setPluginActive(pluginName, self.checkBox.isChecked())

        if self.pluginManager.requiresApplicationRestart:
            statusLabel: QtWidgets.QLabel = self.pluginManagerViewer.widget.statusLabel
            statusLabel.setText('Restart required.')

            restartAppButton: QtWidgets.QPushButton = self.pluginManagerViewer.widget.restartApplicationButton
            restartAppButton.setVisible(True)

        if pluginInfo and pluginInfo.pluginLoadingError:
            self.infoLabel.setText(pluginInfo.pluginLoadingError)
            self.checkBox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.infoLabel.setText('')
    