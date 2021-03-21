from typing import Callable
import asset_manager

class InputConfirmDialog(object):
    def __init__(self, confirmInputText: str, onAccept: Callable, title: str = None, confirmButtonText: str = None) -> None:
        super().__init__()

        self.dialog = asset_manager.loadDialog('inputConfirmDialog.ui')
        if title:
            self.dialog.setWindowTitle(title)
        
        self.confirmInputText = confirmInputText
        self.dialog.confirmButton.clicked.connect(self.dialog.accept)
        self.dialog.cancelButton.clicked.connect(self.dialog.reject)
        self.dialog.confirmInputEdit.textChanged.connect(self.onConfirmInputEditTextChanged)

        if confirmButtonText:
            self.dialog.confirmButton.setText(confirmButtonText)

        self.dialog.accepted.connect(onAccept)

        self.dialog.textLabel.setText(f'Please enter {confirmInputText}')

    def onConfirmInputEditTextChanged(self, txt: str):
        self.dialog.confirmButton.setEnabled(txt == self.confirmInputText)

    def setText(self, text: str):
        self.dialog.textLabel.setText(text)
        
    def setTitle(self, title: str):
        self.dialog.setWindowTitle(title)

    def open(self):
        self.dialog.show()

    def close(self):
        self.dialog.close()