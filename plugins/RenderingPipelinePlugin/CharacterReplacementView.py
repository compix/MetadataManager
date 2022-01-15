import typing
from PySide2 import QtWidgets, QtGui, QtCore
from MetadataManagerCore.Event import Event
from RenderingPipelinePlugin import PipelineKeys
import qt_util

NamingConventions = [
    'All',
    PipelineKeys.SidNaming,
    PipelineKeys.BaseSceneNaming,
    PipelineKeys.RenderSceneNaming,
    PipelineKeys.InputSceneNaming,
    PipelineKeys.CreatedInputSceneNaming,
    PipelineKeys.EnvironmentSceneNaming,
    PipelineKeys.NukeSceneNaming,
    PipelineKeys.BlenderCompositingSceneNaming,
    PipelineKeys.RenderingNaming,
    PipelineKeys.PostNaming,
    PipelineKeys.DeliveryNaming
]

class ReplacedCharInfo(object):
    def __init__(self, parentLayout: QtWidgets.QVBoxLayout, targetNaming:str = None, replacedChar: str = None, replacementChar: str = None) -> None:
        super().__init__()

        self.replacedCharEdit = QtWidgets.QLineEdit()
        self.replacedCharEdit.setPlaceholderText('Character to replace')
        self.replacementCharEdit = QtWidgets.QLineEdit()
        self.replacementCharEdit.setPlaceholderText('Replacement character')

        self.layout = QtWidgets.QHBoxLayout()
        parentLayout.addLayout(self.layout)

        self.namingComboBox = QtWidgets.QComboBox()
        self.namingComboBox.addItems(NamingConventions)
        self.namingComboBox.setEditable(False)

        self.layout.addWidget(QtWidgets.QLabel('Naming Target: '))
        self.layout.addWidget(self.namingComboBox)
        self.layout.addWidget(self.replacedCharEdit)

        self.arrowIcon = QtGui.QIcon(':/icons/arrow-point-to-right.png')
        
        self.arrowLabel = QtWidgets.QLabel()
        self.arrowLabel.setPixmap(self.arrowIcon.pixmap(self.arrowIcon.actualSize(QtCore.QSize(16, 16))))
        self.layout.addWidget(self.arrowLabel)
        self.layout.addWidget(self.replacementCharEdit)

        deleteButton = QtWidgets.QPushButton()
        deleteButton.setIcon(QtGui.QIcon(':/icons/delete.png'))
        deleteButton.clicked.connect(self.onDeleteClick)
        self.layout.addWidget(deleteButton)

        self.onDeleted = Event()
        
        if targetNaming:
            self.namingComboBox.setCurrentText(targetNaming)

        if replacedChar:
            self.replacedCharEdit.setText(replacedChar)

        if replacementChar:
            self.replacementCharEdit.setText(replacementChar)

    def onDeleteClick(self):
        self.delete()

    def delete(self, fireEvent = True):
        qt_util.clearContainer(self.layout)
        self.layout.deleteLater()

        if fireEvent:
            self.onDeleted(self)

class CharacterReplacementView(object):
    def __init__(self, renderingPipelineDialog) -> None:
        super().__init__()

        self.replacedCharInfos: typing.List[ReplacedCharInfo] = []

        self.frame: QtWidgets.QFrame = renderingPipelineDialog.replacedCharactersFrame
        self.addButton = renderingPipelineDialog.addReplacedCharacterButton

        self.addButton.clicked.connect(self.onAddClick)

    def load(self, envSettings: dict):
        for rc in self.replacedCharInfos:
            rc.delete(False)

        self.replacedCharInfos.clear()
        
        replacedChars = envSettings.get(PipelineKeys.CharactersToReplaceInNamingConvention)
        if replacedChars:
            for targetNaming, charToReplace, replacementChar in replacedChars:
                self.add(targetNaming, charToReplace, replacementChar)

    def save(self, envSettings: dict):
        envSettings[PipelineKeys.CharactersToReplaceInNamingConvention] = self.replacedChars

    @property
    def replacedChars(self) -> typing.List[typing.Tuple[str, str, str]]:
        return [(i.namingComboBox.currentText(), i.replacedCharEdit.text(), i.replacementCharEdit.text()) for i in self.replacedCharInfos]

    def add(self, targetNaming: str = None, charToReplace: str = None, replacementChar: str = None):
        info = ReplacedCharInfo(self.frame.layout(), targetNaming, charToReplace, replacementChar)
        self.replacedCharInfos.append(info)
        info.onDeleted.subscribe(self.onReplacedCharInfoDeleted)

    def onAddClick(self):
        self.add()

    def onReplacedCharInfoDeleted(self, info: ReplacedCharInfo):
        self.replacedCharInfos.remove(info)