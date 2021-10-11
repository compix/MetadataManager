from ServiceRegistry import ServiceRegistry
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore.Event import Event

ENVIRONMENT_MANAGER : EnvironmentManager = None
DB_MANAGER : MongoDBManager = None
SERVICE_REGISTRY : ServiceRegistry = None

ON_INITIALIZED = Event()