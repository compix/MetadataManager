
from ApplicationMode import ApplicationMode


class AppInfo(object):
    def __init__(self):
        super().__init__()

        self.appInfo : str = None
        self.company : str = None
        self.initialized : bool = False
        self.applicationQuitting : bool = False
        self.mode : ApplicationMode = None