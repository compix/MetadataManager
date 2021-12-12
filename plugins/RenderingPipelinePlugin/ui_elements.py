import os
import typing
from PySide2 import QtWidgets
from PySide2.QtGui import QIcon

from node_exec import windows_nodes
from qt_extensions import qt_util

class UIElement(object):
    def __init__(self, layout: QtWidgets.QLayout) -> None:
        super().__init__()

        self.layout = layout

    def addToLayout(self, widgets):
        if self.layout:
            if isinstance(widgets, list):
                for w in widgets:
                    self.layout.addWidget(w)
            else:
                self.layout.addWidget(widgets)

class FileSelectionElement(UIElement):
    def __init__(self, parentWidget, layout: QtWidgets.QLayout, showSelectInExplorerButton=True, isFolder=False, fileFilter="Any File (*.*)", createLayoutIfUnspecified=True) -> None:
        if not layout and createLayoutIfUnspecified:
            layout = QtWidgets.QHBoxLayout()

        super().__init__(layout)

        self.isFolder = isFolder
        self.parentWidget = parentWidget
        self.fileFilter = fileFilter
        self.edit = QtWidgets.QLineEdit()
        self.addToLayout(self.edit)
        
        if showSelectInExplorerButton:
            self.selectInExplorerButton = QtWidgets.QPushButton()
            self.selectInExplorerButton.setToolTip('Select in explorer.')
            self.selectInExplorerButton.setIcon(QIcon(':/icons/select.png'))
            self.addToLayout(self.selectInExplorerButton)

            self.selectInExplorerButton.clicked.connect(self.onSelectInExplorerButtonClicked)
            
        self.selectButton = QtWidgets.QPushButton()
        self.selectButton.setToolTip('Choose file.')
        self.addToLayout(self.selectButton)
        if isFolder:
            self.selectButton.clicked.connect(self.onSelectFolder)
            self.selectButton.setIcon(QIcon(':/icons/folder.png'))
        else:
            self.selectButton.clicked.connect(self.onSelectFile)
            self.selectButton.setIcon(QIcon(':/icons/file.png'))

    def onSelectInExplorerButtonClicked(self):
        try:
            windows_nodes.selectInExplorer(self.edit.text())
        except:
            pass

    def onSelectFile(self):
        initialDir = os.path.dirname(self.edit.text()) if os.path.exists(self.edit.text()) else None
        fileName,_ = QtWidgets.QFileDialog.getOpenFileName(self.parentWidget, "Open", initialDir, filter=self.fileFilter)
        if fileName != None and fileName != "":
            self.edit.setText(fileName)

    def onSelectFolder(self):
        initialDir = self.edit.text() if os.path.exists(self.edit.text()) else None
        dirName = QtWidgets.QFileDialog.getExistingDirectory(self.parentWidget, "Open", initialDir)
        if dirName != None and dirName != "":
            self.edit.setText(dirName)
    
class ComboBoxElement(UIElement):
    def __init__(self, layout: QtWidgets.QLayout, items: typing.List[str]=None) -> None:
        super().__init__(layout)

        self.comboBox = QtWidgets.QComboBox()
        if items:
            self.comboBox.addItems(items)
        self.addToLayout(self.comboBox)
