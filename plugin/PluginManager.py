from MetadataManagerCore import Keys
from AppInfo import AppInfo
from MetadataManagerCore.Event import Event
from MetadataManagerCore.mongodb_manager import MongoDBManager
from plugin.Plugin import Plugin
from typing import Dict, List
import importlib
import os
import sys
import logging
import typing

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from ServiceRegistry import ServiceRegistry
    from viewers.ViewerRegistry import ViewerRegistry

class PluginInfo(object):
    def __init__(self, pluginFolder: str) -> None:
        super().__init__()

        self.pluginFolder = pluginFolder
        self.pluginInstance: Plugin = None
        self.pluginLoadingError: str = None
        self.pluginActive_ = False
        self.onActiveStatusChanged: Event = Event()

    @property
    def pluginActive(self):
        return self.pluginActive_

    @pluginActive.setter
    def pluginActive(self, value: bool):
        prevValue = self.pluginActive_
        self.pluginActive_ = value

        if prevValue != self.pluginActive_:
            self.onActiveStatusChanged(self.pluginActive_)

    @property
    def pluginName(self):
        return os.path.basename(self.pluginFolder)

class PluginManager(object):
    def __init__(self, defaultPluginsFolders: List[str], serviceRegistry: 'ServiceRegistry', appInfo: AppInfo) -> None:
        super().__init__()

        self.pluginsFolders = set()
        self.defaultPluginsFolders = [folder.replace('\\', '/') for folder in defaultPluginsFolders]
        self.viewerRegistry: 'ViewerRegistry' = None
        self.serviceRegistry = serviceRegistry
        self.appInfo = appInfo

        self.pluginInfoMap: Dict[str,PluginInfo] = dict()
        self.requiresApplicationRestart = False
        self.settings = None
        self.dbManager: MongoDBManager = None
        self.pluginActiveStatus = dict()
        self.pluginAutoActivateStatus = dict()
        self.onPluginAutoactivateStatusChanged = Event()
        self.onPluginAdded = Event()
        self.onPluginRemoved = Event()

        for pluginsFolder in defaultPluginsFolders:
            self.addPluginsFolder(pluginsFolder)

    def setPluginAutoactivateState(self, pluginName: str, autoactivate: bool):
        curAutoactivate = self.getPluginAutoactivateState(pluginName)
        if curAutoactivate != autoactivate:
            self.pluginAutoActivateStatus[pluginName] = autoactivate
            self.onPluginAutoactivateStatusChanged(pluginName, autoactivate)

    def getPluginAutoactivateState(self, pluginName: str):
        return self.pluginAutoActivateStatus.get(pluginName, True)

    def addPluginsFolder(self, pluginsFolder: str):
        pluginsFolder = pluginsFolder.replace('\\', '/')
        if pluginsFolder in self.pluginsFolders:
            return False

        if not os.path.exists(pluginsFolder):
            logger.error(f'The plugins folder {pluginsFolder} does not exist.')
            return False

        # The plugins folder must contain a __init__.py
        if not os.path.exists(os.path.join(pluginsFolder, '__init__.py')):
            logger.error(f'The plugins folder {pluginsFolder} does not have an __init__.py file.')
            return False
        
        sys.path.append(pluginsFolder)
        self.pluginsFolders.add(pluginsFolder)

        # Go through the subdirectories of the plugins folder to add the plugin info
        for root,dirs,_ in os.walk(pluginsFolder):
            for pluginFolder in dirs:
                if pluginFolder == '__pycache__':
                    continue

                if pluginFolder in self.pluginInfoMap:
                    logger.warning(f'The plugin {pluginFolder} was already added.')
                    continue
                
                fullPluginFolderPath = os.path.join(root, pluginFolder)
                self.pluginInfoMap[pluginFolder] = PluginInfo(fullPluginFolderPath)
                self.onPluginAdded(pluginFolder)

            break

        if not pluginsFolder in self.defaultPluginsFolders:
            self.saveDbState(self.serviceRegistry.dbManager)

        return True

    def refreshAvailablePlugins(self):
        pluginNames = set()
        for pluginFolder in self.pluginsFolders:
            for root,dirs,_ in os.walk(pluginFolder):
                for pluginFolder in dirs:
                    if pluginFolder == '__pycache__':
                        continue

                    pluginNames.add(pluginFolder)

                    if pluginFolder in self.pluginInfoMap:
                        continue
                    
                    fullPluginFolderPath = os.path.join(root, pluginFolder)
                    self.pluginInfoMap[pluginFolder] = PluginInfo(fullPluginFolderPath)
                    self.onPluginAdded(pluginFolder)

                break

        deletedPluginNames = set(self.pluginInfoMap.keys()) - pluginNames
        for deletedPluginName in deletedPluginNames:
            del self.pluginInfoMap[deletedPluginName]
            self.onPluginRemoved(deletedPluginName)

    def removePluginsFolder(self, pluginsFolder: str):
        pluginsFolder = pluginsFolder.replace('\\', '/')
        if not pluginsFolder in self.pluginsFolders:
            return
        
        self.pluginsFolders.remove(pluginsFolder)
        sys.path.remove(pluginsFolder)

        # Go through the subdirectories of the plugins folder to remove the plugin info
        for _,dirs,_ in os.walk(pluginsFolder):
            for pluginFolder in dirs:
                if pluginFolder == '__pycache__':
                    continue
                
                if not pluginFolder in self.pluginInfoMap:
                    continue

                del self.pluginInfoMap[pluginFolder]
                self.onPluginRemoved(pluginFolder)

            break

        self.saveDbState(self.serviceRegistry.dbManager)

    def getNonDefaultPluginsFolders(self):
        return [folder for folder in self.pluginsFolders if not folder in self.defaultPluginsFolders]

    def getPluginInstanceByName(self, name: str):
        return self.pluginInfoMap.get(name, PluginInfo(None)).pluginInstance

    def refreshPluginState(self):
        for pluginName in self.availablePluginNames:
            active = self.pluginActiveStatus.get(pluginName, True)
            autoactivate = self.getPluginAutoactivateState(pluginName)
            if active or autoactivate:
                try:
                    self.setPluginActive(pluginName, active or autoactivate)
                except Exception as e:
                    logger.error(str(e))

    def setViewerRegistry(self, viewerRegistry: 'ViewerRegistry'):
        self.viewerRegistry = viewerRegistry

    @property
    def availablePluginNames(self):
        return [pluginName for pluginName in self.pluginInfoMap.keys()]

    def setPluginActive(self, pluginName: str, active: bool, loadingPluginNames: List[str] = None):
        pluginInfo = self.pluginInfoMap.get(pluginName)

        if not pluginInfo:
            raise RuntimeError(f'Could not find plugin info for plugin {pluginName}')

        if active and pluginInfo.pluginInstance and pluginInfo.pluginActive:
            # Already active
            return

        if active and not pluginInfo.pluginInstance:
            self.addPlugin(pluginInfo, loadingPluginNames or [])

        if not active and pluginInfo.pluginInstance:
            self.requiresApplicationRestart = True
            pluginInfo.pluginActive = False

        # Save the state:
        self.save(self.settings, self.dbManager)

    def addPlugin(self, pluginInfo: PluginInfo, loadingPluginNames: List[str] = None):
        pluginName = pluginInfo.pluginName

        try:
            if pluginName in (loadingPluginNames or []):
                raise RuntimeError(f'Circular dependency found when loading plugin {pluginName}: {loadingPluginNames}')
                
            loadingPluginNames.append(pluginName)
            pluginFolder = pluginInfo.pluginFolder
            logger.debug(f'Importing plugin {pluginFolder}.')

            # The plugin folder must contain a .py file with the same name as the pluginFolder:
            pluginMainFile = os.path.join(pluginFolder, pluginName + '.py')

            if not os.path.exists(pluginMainFile):
                raise RuntimeError(f'The main plugin python file {pluginMainFile} does not exist.')

            pluginModule = importlib.import_module(f'{pluginName}.{pluginName}')
            importlib.reload(pluginModule)

            pluginClass = getattr(pluginModule, pluginName, None)
            if pluginClass == None:
                raise RuntimeError(f'The plugin python file must contain a class with the same name {pluginName}')

            # Check for dependencies:
            if pluginClass.dependentPluginNames() and len(pluginClass.dependentPluginNames()) > 0:
                try:
                    for depPlugin in pluginClass.dependentPluginNames():
                        self.setPluginActive(depPlugin, True, loadingPluginNames=loadingPluginNames)
                except Exception as e:
                    raise RuntimeError(f'Failed to load plugin {pluginName} because one of its dependencies failed to load: {str(e)}')
            
            pluginInstance: Plugin = pluginClass()
            pluginInstance.viewerRegistry = self.viewerRegistry
            pluginInstance.serviceRegistry = self.serviceRegistry
            pluginInstance.appInfo = self.appInfo
            pluginInfo.pluginInstance = pluginInstance
            pluginInfo.pluginLoadingError = None

            pluginInstance.init()
            pluginInfo.pluginActive = True
        except Exception as e:
            pluginLoadingError = f'Failed to import plugin {pluginName} because an exception occurred: {str(e)}'
            logger.error(pluginLoadingError)

            pluginInfo.pluginInstance = None
            pluginInfo.pluginLoadingError = pluginLoadingError
            pluginInfo.pluginActive = False

    def saveDbState(self, dbManager: MongoDBManager):
        dbState = {
            'plugin_autoactivate_status': self.pluginAutoActivateStatus,
            'plugins_folders': self.getNonDefaultPluginsFolders()
        }
        dbManager.stateCollection.update_one({'_id': "plugin_manager"}, {'$set': dbState}, upsert=True)

    def save(self, settings, dbManager: MongoDBManager):
        """
        Serializes the state in settings and/or in the database.

        input:
            - settings: Must support settings.setValue(key: str, value)
            - dbManager: MongoDBManager
        """
        settings.setValue("plugin_manager", {
            'plugin_active_status': {pluginInfo.pluginName:pluginInfo.pluginActive for pluginInfo in self.pluginInfoMap.values()}
        })

        self.saveDbState(dbManager)

    def load(self, settings, dbManager: MongoDBManager):
        """
        Loads the state from settings and/or the database.

        input:
            - settings: Must support settings.value(str)
            - dbManager: MongoDBManager
        """
        self.settings = settings
        self.dbManager = dbManager

        infoDict = settings.value("plugin_manager")
        dbInfoDict = self.dbManager.stateCollection.find_one({'_id': "plugin_manager"})

        if infoDict == None:
            infoDict = dict()

        pluginsFolders = dbInfoDict.get('plugins_folders', set())
        for pluginsFolder in pluginsFolders:
            self.addPluginsFolder(pluginsFolder)

        self.pluginActiveStatus = infoDict.get('plugin_active_status', dict())
        if dbInfoDict:
            for pluginName, autoactivate in dbInfoDict.get('plugin_autoactivate_status').items():
                self.setPluginAutoactivateState(pluginName, autoactivate)
        else:
            self.pluginAutoActivateStatus = dict()

        self.refreshPluginState()

    def shutdown(self):
        for plugin in self.pluginInfoMap.values():
            if plugin.pluginInstance:
                plugin.pluginInstance.shutdown()