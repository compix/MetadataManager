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

        self.dbManager : MongoDBManager = None
        self.actionManager : ActionManager = None
        self.environmentManager : EnvironmentManager = None
        self.codeGenerator : CodeGenerator = None
        self.deadlineService : DeadlineService= None
        self.visualScripting : ExtendedVisualScripting = None
        self.taskProcessor : TaskProcessor = None