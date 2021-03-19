import typing
from AppInfo import AppInfo

if typing.TYPE_CHECKING:
    from viewers.ViewerRegistry import ViewerRegistry
    from ServiceRegistry import ServiceRegistry

class Plugin(object):
    def __init__(self) -> None:
        super().__init__()

        self.serviceRegistry: "ServiceRegistry" = None
        self.viewerRegistry: "ViewerRegistry" = None
        self.appInfo: AppInfo = None

    def init(self):
        pass