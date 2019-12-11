from qt_extensions.DockWidget import DockWidget
from assets import asset_manager

class SettingsViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Settings", parentWindow, asset_manager.getUIFilePath("settings.ui"))