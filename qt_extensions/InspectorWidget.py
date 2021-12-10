from MetadataManagerCore.Event import Event
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
from typing import Any
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from enum import Enum
import json

class InspectorWidgetType(Enum):
    String = 'String'
    Integer = 'Integer'
    Float = 'Float'
    Boolean = 'Boolean'
    Dictionary = 'Dictionary'
    List = 'List'

class InspectorWidget(object):
    def __init__(self, value: Any = None, editable = True) -> None:
        super().__init__()

        self.widget = None

        self._setValueFunction = None
        self._getValueFunction = None
        self._setWidgetEditableFunction = None
        self._isEditable = editable
        self._widgetType = None
        self.onReturnPressedEvent = Event()

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

    def constructFromInspectorWidgetType(self, widgetType: InspectorWidgetType, value: Any = None):
        if widgetType == InspectorWidgetType.String:
            self.widget = QtWidgets.QLineEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getStringValue
            self._setValueFunction = self._setStringValue
            self._widgetType = InspectorWidgetType.String
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or ''

        elif widgetType == InspectorWidgetType.Integer:
            self.widget = QtWidgets.QLineEdit()
            self.widget.setValidator(RegexPatternInputValidator('^\d*$'))
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getIntValue
            self._setValueFunction = self._setIntValue
            self._widgetType = InspectorWidgetType.Integer
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or 0

        elif widgetType == InspectorWidgetType.Boolean:
            self.widget = QtWidgets.QCheckBox('')
            self.widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            self._setWidgetEditableFunction = self._setCheckBoxEditable
            self._getValueFunction = self._getBoolValue
            self._setValueFunction = self._setBoolValue
            self._widgetType = InspectorWidgetType.Boolean
            self.value = value or False

        elif widgetType == InspectorWidgetType.Float:
            self.widget = QtWidgets.QLineEdit()
            self.widget.setValidator(RegexPatternInputValidator('^[+-]?([0-9]*[.])?[0-9]*$'))
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getFloatValue
            self._setValueFunction = self._setFloatValue
            self._widgetType = InspectorWidgetType.Float
            self.widget.returnPressed.connect(lambda: self.onReturnPressedEvent())
            self.value = value or 0.0

        elif widgetType == InspectorWidgetType.Dictionary:
            self.widget = QtWidgets.QTextEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getDictValue
            self._setValueFunction = self._setDictValue
            self._widgetType = InspectorWidgetType.Dictionary
            self.value = value or dict()

        elif widgetType == InspectorWidgetType.List:
            self.widget = QtWidgets.QTextEdit()
            self._setWidgetEditableFunction = self._setLineEditEditable
            self._getValueFunction = self._getDictValue
            self._setValueFunction = self._setDictValue
            self._widgetType = InspectorWidgetType.List
            self.value = value or []

        else:
            raise RuntimeError('Unsupported widget type: ' + widgetType.value)

    def _setCheckBoxEditable(self):
        self.widget.setAttribute(Qt.WA_TransparentForMouseEvents, not self._isEditable)
        self.widget.setFocusPolicy(Qt.StrongFocus if self._isEditable else Qt.NoFocus)

    def _setLineEditEditable(self):
        self.widget.setReadOnly(not self._isEditable)

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

    def _getBoolValue(self):
        return self.widget.isChecked()
    
    def _setBoolValue(self, value: bool):
        self.widget.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)

    def _getDictValue(self):
        return json.loads(self.widget.toPlainText())

    def _setDictValue(self, value: dict):
        self.widget.setPlainText(json.dumps(value, sort_keys=True, indent=4))