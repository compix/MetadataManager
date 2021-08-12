from typing import List
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton
import PySide2

class RowSkipConditionUIElement(QHBoxLayout):
    def __init__(self, header: List[str], parent: PySide2.QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.addWidget(QLabel("Skip if"))
        self.headerComboBox = QComboBox()
        self.headerComboBox.addItems(header)
        self.addWidget(self.headerComboBox)
        self.operatorComboBox = QComboBox()
        self.operatorComboBox.addItems(['==', '!=', '>', '>=', '<', '<='])
        self.addWidget(self.operatorComboBox)
        self.valueEdit = QLineEdit()
        self.addWidget(self.valueEdit)
        self.deleteButton = QPushButton()
        self.deleteButton.setIcon(QIcon(':/icons/delete.png'))
        self.addWidget(self.deleteButton)

        self.operations = {
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '>':  lambda x, y: x >  y,
            '>=': lambda x, y: x >= y,
            '<':  lambda x, y: x <  y,
            '<=': lambda x, y: x <= y
        }

        self.raiseErrorOnMissingKeys = False

    def evaluateCondition(self, rowDictionary: dict):
        key = self.headerComboBox.currentText()
        if not key in rowDictionary:
            if self.raiseErrorOnMissingKeys:
                raise RuntimeError(f'The header cell {key} does not exist in the given row.')
            else:
                return True
            
        operator = self.operatorComboBox.currentText()

        value = self.valueEdit.text()
        return self.operations[operator](rowDictionary[key], value)

    def getAsDict(self):
        return {
            'headerKey': self.headerComboBox.currentText(),
            'operator': self.operatorComboBox.currentText(),
            'value': self.valueEdit.text()
        }

    def setFromDict(self, d: dict):
        self.headerComboBox.setCurrentText(d.get('header_key'))
        self.operatorComboBox.setCurrentText(d.get('operator'))
        self.valueEdit.setText(d.get('value'))