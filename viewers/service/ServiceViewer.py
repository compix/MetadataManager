from MetadataManagerCore.service.ServiceManager import ServiceManager
from MetadataManagerCore.service.Service import ServiceStatus

class ServiceViewer(object):
    def __init__(self, serviceRegistry) -> None:
        super().__init__()

        self.serviceRegistry = serviceRegistry

    @property
    def widget(self):
        return None

    def getServiceInfoDict(self, serviceClassName: str, serviceName: str, serviceDescription: str, initialStatus: ServiceStatus):
        baseInfoDict = ServiceManager.createBaseServiceInfoDictionary(serviceClassName, serviceName, serviceDescription, initialStatus)
        return baseInfoDict