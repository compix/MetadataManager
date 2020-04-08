import sys
from PySide2.QtWidgets import QApplication
from viewers import resources_qrc
from LoaderWindow import LoaderWindow
import os, PySide2

# Make sure the PySide2 plugin can be found:
dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

if __name__ == "__main__":
    app = QApplication([])

    LoaderWindow(app)

    sys.exit(app.exec_())