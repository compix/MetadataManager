
from PySide2 import QtCore
from ApplicationMode import ApplicationMode


class AppInfo(object):
    def __init__(self):
        super().__init__()

        self.appName : str = None
        self.company : str = None
        self.initialized : bool = False
        self.applicationQuitting : bool = False
        self.mode : ApplicationMode = None

    @property
    def settings(self) -> QtCore.QSettings:
        return QtCore.QSettings(self.company, self.appName)