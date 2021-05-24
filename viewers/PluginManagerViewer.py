from plugin.PluginManager import PluginManager
from qt_extensions.DockWidget import DockWidget
import asset_manager
from PySide2 import QtWidgets
from PySide2.QtCore import Qt

class PluginManagerViewer(DockWidget):
    def __init__(self, parentWindow: QtWidgets.QWidget, pluginManager: PluginManager, requestRestartFunction):
        super().__init__("Plugin Manager", parentWindow, asset_manager.getUIFilePath("pluginManager.ui"))
        
        self.pluginManager = pluginManager
        self.pluginTableWidget: QtWidgets.QTableWidget = self.widget.pluginTableWidget
        self.widget.statusLabel.setText('')

        self.requestRestartFunction = requestRestartFunction
        self.widget.restartApplicationButton.setVisible(False)
        self.widget.restartApplicationButton.clicked.connect(self.onApplicationRestartRequest)
        
        self.setupPluginList()

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
        rowCount = len(self.pluginManager.availablePluginNames)
        self.pluginTableWidget.setRowCount(rowCount)

        for rowIdx, pluginName in enumerate(self.pluginManager.availablePluginNames):
            pluginInfo = self.pluginManager.pluginInfoMap.get(pluginName)

            activeCheckbox = QtWidgets.QCheckBox()
            onActiveStatusChanged = lambda checkbox: lambda pluginActive: checkbox.setChecked(pluginActive)
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

        self.pluginManager.onPluginAutoactivateStatusChanged.subscribe(self.onPluginAutoactivateStatusChanged)

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
    