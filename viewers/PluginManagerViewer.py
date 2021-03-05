from plugin.PluginManager import PluginManager
from qt_extensions.DockWidget import DockWidget
import asset_manager
from PySide2 import QtWidgets
from PySide2.QtCore import Qt

class PluginManagerViewer(DockWidget):
    def __init__(self, parentWindow: QtWidgets.QWidget, pluginManager: PluginManager, requestRestartFunction):
        super().__init__("Plugin Manager", parentWindow, asset_manager.getUIFilePath("pluginManager.ui"))
        
        self.pluginManager = pluginManager
        self.pluginListWidget: QtWidgets.QListWidget = self.widget.pluginListWidget
        self.widget.statusLabel.setText('')

        self.requestRestartFunction = requestRestartFunction
        self.widget.restartApplicationButton.setVisible(False)
        self.widget.restartApplicationButton.clicked.connect(self.onApplicationRestartRequest)

        self.setupPluginList()

    def onApplicationRestartRequest(self):
        self.requestRestartFunction()

    def setupPluginList(self):
        for pluginName in self.pluginManager.availablePluginNames:
            pluginInfo = self.pluginManager.pluginInfoMap.get(pluginName)

            layout = QtWidgets.QHBoxLayout()

            widget = QtWidgets.QWidget()
            widget.setLayout(layout)

            activeCheckbox = QtWidgets.QCheckBox()
            onActiveStatusChanged = lambda checkbox: lambda pluginActive: checkbox.setChecked(pluginActive)
            pluginInfo.onActiveStatusChanged.subscribe(onActiveStatusChanged(activeCheckbox))

            activeCheckbox.setText(pluginName)

            layout.addWidget(activeCheckbox)

            infoLabel = QtWidgets.QLabel()
            infoLabel.setText('')
            infoLabel.setStyleSheet("color: red") 
            layout.addWidget(infoLabel)
            layout.setAlignment(Qt.AlignLeft)
            
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.pluginListWidget.addItem(item)
            self.pluginListWidget.setItemWidget(item, widget)

            activeCheckbox.stateChanged.connect(PluginCheckboxStateChangeHandler(self, activeCheckbox, infoLabel))

class PluginCheckboxStateChangeHandler(object):
    def __init__(self, pluginManagerViewer: PluginManagerViewer, pluginCheckBox: QtWidgets.QCheckBox, infoLabel: QtWidgets.QLabel) -> None:
        super().__init__()

        self.pluginManagerViewer = pluginManagerViewer
        self.pluginManager = self.pluginManagerViewer.pluginManager
        self.checkBox = pluginCheckBox
        self.infoLabel = infoLabel

    def __call__(self, changed):
        pluginName = self.checkBox.text()
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
    