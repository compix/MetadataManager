import sys
from PySide2.QtWidgets import QApplication
from LoaderWindow import LoaderWindow

if __name__ == "__main__":
    app = QApplication([])

    LoaderWindow(app)

    sys.exit(app.exec_())