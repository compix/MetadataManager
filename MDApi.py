from ServiceRegistry import ServiceRegistry
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.mongodb_manager import MongoDBManager

ENVIRONMENT_MANAGER : EnvironmentManager = None
DB_MANAGER : MongoDBManager = None
SERVICE_REGISTRY : ServiceRegistry = None