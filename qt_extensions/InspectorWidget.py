from msilib.schema import ComboBox
import typing
from MetadataManagerCore.Event import Event
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
from typing import Any
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from enum import Enum
import json
import os
from qt_extensions import ui_elements

class InspectorWidgetType(Enum):
    String = 'String'
    Integer = 'Integer'
    Float = 'Float'
    Boolean = 'Boolean'
    Dictionary = 'Dictionary'
    List = 'List'
    ComboBox = 'ComboBox'
    Folder = 'Folder'
    File = 'File'

def getInitialDir(filename: str, relFolder: str, isFolder=False):
    if not os.path.isabs(filename):
        filename = os.path.join(relFolder, filename)

    if isFolder:
        return filename
    else:
        return os.path.dirname(filename)

def connectRelativeFolderSelection(lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, relativeFolder: str = None):
    def onSelect():
        if relativeFolder:
            initialDir = getInitialDir(lineEdit.text(), relativeFolder)
            dirName = QtWidgets.QFileDialog.getExistingDirectory(None, "Open", initialDir)
        else:
            dirName = QtWidgets.QFileDialog.getExistingDirectory(None, "Open")

        if dirName != None and dirName != "":
            if os.path.normpath(dirName).startswith(os.path.normpath(relativeFolder)):
                dirName = os.path.relpath(dirName, relativeFolder)

            lineEdit.setText(dirName)
    
    try:
        button.clicked.disconnect()
    except:
        pass
    button.clicked.connect(onSelect)

def connectRelativeFileSelection(renderingPipelineViewer, lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, filter=""):
    def onSelect():
        baseProjectFolder = renderingPipelineViewer.baseProjectFolderPath
        initialDir = getInitialDir(lineEdit.text(), baseProjectFolder)
        filename,_ = QtWidgets.QFileDialog.getOpenFileName(renderingPipelineViewer.dialog, "Open", initialDir, filter=filter)
        if filename:
            if os.path.normpath(filename).startswith(os.path.normpath(baseProjectFolder)):
                filename = os.path.relpath(filename, baseProjectFolder)

            lineEdit.setText(filename)
    
    try:
        button.clicked.disconnect()
    except:
        pass
    button.clicked.connect(onSelect)

class InspectorWidget(object):
    def __init__(self, value: Any = None, editable = True) -> None:
        super().__init__()

        self.widget: QtWidgets.QWidget = None
        self.layout: QtWidgets.QLayout = None

        self._setValueFunction = None
        self._getValueFunction = None
        self._setWidgetEditableFunction = None
        self._isEditable = editable
        self._widgetType = None
        self.onReturnPressedEvent = Event()
        self.onValueChanged = Event()

        if value != None:
            self.constructWidgetFromValue(value)

    @property
    def value(self):
        return self._getValueFunction()

    @value.setter
    def value(self, v: Any):
        self._setValueFunction(v)

    @property
    def isEditable(self):
        return self._isEditable

    @isEditable.setter
    def isEditable(self, value: bool):
        valueChanged = value != self._isEditable

        if valueChanged:
            self._isEditable = value
            self._setWidgetEditableFunction()

    @property
    def type(self) -> InspectorWidgetType:
        return self._widgetType

    def constructWidgetFromValue(self, value: Any):
        if isinstance(value, str):
            self.constructFromInspectorWidgetType(InspectorWidgetType.String)

        elif isinstance(value, bool):
            self.constructFromInspectorWidgetType(InspectorWidgetType.Boolean)
            
        elif isinstance(value, int):
            self.constructFromInspectorWidgetType(InspectorWidgetType.Integer)

        elif isinstance(value, float):
            self.constructFromInspectorWidgetType(InspectorWidgetType.Float)

        elif isinstance(value, dict):
            self.constructFromInspectorWidgetType(InspectorWidgetType.Dictionary)

        elif isinstance(value, list):
            self.constructFromInspectorWidgetType(InspectorWidgetType.List)

        else:
            raise RuntimeError('Unsupported value type: ' + str(type(value)))

        self._setWidgetEditableFunction()
        self.value = value

        return self.widget

    def constructFromInspectorWidgetType(self, widgetType: InspectorWidgetType, value: Any = None, fileFilter="Any File (*.*)", comboBoxItems: typing.List[str] = None):
        self.onValueChanged.clear()

        if widgetType == InspectorWidgetType.String:
            self.widget = QtWidgets.QLineEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getStringValue
            self._setValueFunction = self._setStringValue
            self._widgetType = InspectorWidgetType.String
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or ''
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.Integer:
            self.widget = QtWidgets.QLineEdit()
            self.widget.setValidator(RegexPatternInputValidator('^\d*$'))
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getIntValue
            self._setValueFunction = self._setIntValue
            self._widgetType = InspectorWidgetType.Integer
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or 0
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.Boolean:
            self.widget = QtWidgets.QCheckBox('')
            self.widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            self._setWidgetEditableFunction = self._setCheckBoxEditable
            self._getValueFunction = self._getBoolValue
            self._setValueFunction = self._setBoolValue
            self._widgetType = InspectorWidgetType.Boolean
            self.value = value or False
            self.widget.stateChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.Float:
            self.widget = QtWidgets.QLineEdit()
            self.widget.setValidator(RegexPatternInputValidator('^[+-]?([0-9]*[.])?[0-9]*$'))
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getFloatValue
            self._setValueFunction = self._setFloatValue
            self._widgetType = InspectorWidgetType.Float
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or 0.0
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.Dictionary:
            self.widget = QtWidgets.QTextEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getDictValue
            self._setValueFunction = self._setDictValue
            self._widgetType = InspectorWidgetType.Dictionary
            self.value = value or dict()
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.List:
            self.widget = QtWidgets.QTextEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getDictValue
            self._setValueFunction = self._setDictValue
            self._widgetType = InspectorWidgetType.List
            self.value = value or []
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.ComboBox:
            self.widget = QtWidgets.QComboBox()
            self._setWidgetEditableFunction = self._setComboBoxEditable
            self._getValueFunction = self._getComboBoxValue
            self._setValueFunction = self._setComboBoxValue
            self._widgetType = InspectorWidgetType.ComboBox
            if comboBoxItems:
                self.widget.addItems(comboBoxItems)

            self.value = value or ''
            self.widget.currentTextChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.Folder:
            folderSelectElement = ui_elements.FileSelectionElement(None, None, isFolder=True)
            self.widget = folderSelectElement.edit
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getStringValue
            self._setValueFunction = self._setStringValue
            self._widgetType = InspectorWidgetType.Folder
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or ''
            self.layout = folderSelectElement.layout
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        elif widgetType == InspectorWidgetType.File:
            folderSelectElement = ui_elements.FileSelectionElement(None, None, fileFilter=fileFilter)
            self.widget = folderSelectElement.edit
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getStringValue
            self._setValueFunction = self._setStringValue
            self._widgetType = InspectorWidgetType.Folder
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or ''
            self.layout = folderSelectElement.layout
            self.widget.textChanged.connect(lambda _: self.onValueChanged(self.value))

        else:
            raise RuntimeError('Unsupported widget type: ' + widgetType.value)

        if not value is None:
            self.onValueChanged(value)

    def _setCheckBoxEditable(self):
        self.widget.setAttribute(Qt.WA_TransparentForMouseEvents, not self._isEditable)
        self.widget.setFocusPolicy(Qt.StrongFocus if self._isEditable else Qt.NoFocus)

    def _setLineEditEditable(self):
        self.widget.setReadOnly(not self._isEditable)

    def _setComboBoxEditable(self):
        self.widget.setEditable(self._isEditable)

    def _getIntValue(self):
        return int(self.widget.text())
    
    def _setIntValue(self, value: int):
        self.widget.setText(str(value))

    def _getFloatValue(self):
        return float(self.widget.text())
    
    def _setFloatValue(self, value: float):
        self.widget.setText(str(value))

    def _getStringValue(self):
        return self.widget.text()
    
    def _setStringValue(self, value: str):
        self.widget.setText(value)

    def _getComboBoxValue(self):
        return self.widget.currentText()
    
    def _setComboBoxValue(self, value: str):
        self.widget.setCurrentText(value)

    def _getBoolValue(self):
        return self.widget.isChecked()
    
    def _setBoolValue(self, value: bool):
        self.widget.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)

    def _getDictValue(self):
        return json.loads(self.widget.toPlainText())

    def _setDictValue(self, value: dict):
        self.widget.setPlainText(json.dumps(value, sort_keys=True, indent=4))