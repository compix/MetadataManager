from AppInfo import AppInfo
from plugin.PluginManager import PluginManager
from MetadataManagerCore.host.HostProcessController import HostProcessController
from MetadataManagerCore.file.FileHandlerManager import FileHandlerManager
from MetadataManagerCore.service.ServiceManager import ServiceManager
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore.third_party_integrations.deadline.deadline_service import DeadlineService
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from VisualScriptingExtensions.CodeGenerator import CodeGenerator
from VisualScriptingExtensions.ExtendedVisualScripting import ExtendedVisualScripting
from MetadataManagerCore.task_processor.TaskProcessor import TaskProcessor

class ServiceRegistry(object):
    def __init__(self):
        super().__init__()

        self.services = []

        self.appInfo : AppInfo = None
        self.dbManager : MongoDBManager = None
        self.actionManager : ActionManager = None
        self.environmentManager : EnvironmentManager = None
        self.codeGenerator : CodeGenerator = None
        self.deadlineService : DeadlineService= None
        self.visualScripting : ExtendedVisualScripting = None
        self.taskProcessor : TaskProcessor = None
        self.documentFilterManager : DocumentFilterManager = None
        self.serviceManager : ServiceManager = None
        self.fileHandlerManager : FileHandlerManager = None
        self.hostProcessController : HostProcessController = None
        self.mainWindowManager = None
        self.pluginManager: PluginManager = None