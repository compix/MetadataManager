import typing

if typing.TYPE_CHECKING:
    from viewers.ViewerRegistry import ViewerRegistry
    from ServiceRegistry import ServiceRegistry

class Plugin(object):
    def __init__(self) -> None:
        super().__init__()

        self.serviceRegistry: "ServiceRegistry" = None
        self.viewerRegistry: "ViewerRegistry" = None

    def init(self):
        pass