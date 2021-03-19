import re

from PySide2.QtGui import QValidator

class RegexPatternInputValidator(QValidator):
    def __init__(self, regexPattern: str) -> None:
        super().__init__()

        self.regexPattern = regexPattern

    def validate(self, input: str, pos: int):
        if re.search(self.regexPattern, input):
            return QValidator.Acceptable

        return QValidator.Invalid