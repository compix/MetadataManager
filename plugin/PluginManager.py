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
    def __init__(self, pluginsFolders: List[str], serviceRegistry: 'ServiceRegistry', appInfo: AppInfo) -> None:
        super().__init__()

        self.pluginsFolders = pluginsFolders
        self.viewerRegistry = None
        self.serviceRegistry = serviceRegistry
        self.appInfo = appInfo

        self.pluginInfoMap: Dict[str,PluginInfo] = dict()
        self.requiresApplicationRestart = False
        self.settings = None
        self.dbManager: MongoDBManager = None
        self.pluginActiveStatus = dict()

        for pluginsFolder in pluginsFolders:
            self.addPluginsFolder(pluginsFolder)

    def addPluginsFolder(self, pluginsFolder: str):
        if not os.path.exists(pluginsFolder):
            logger.error(f'The plugins folder {pluginsFolder} does not exist.')
            return

        # The plugins folder must contain a __init__.py
        if not os.path.exists(os.path.join(pluginsFolder, '__init__.py')):
            logger.error(f'The plugins folder {pluginsFolder} does not have an __init__.py file.')
            return
        
        sys.path.append(pluginsFolder)

        # Go through the subdirectories of the plugins folder to add the plugin info
        for root,dirs,_ in os.walk(pluginsFolder):
            for pluginFolder in dirs:
                if pluginFolder == '__pycache__':
                    continue
                
                fullPluginFolderPath = os.path.join(root, pluginFolder)
                self.pluginInfoMap[pluginFolder] = PluginInfo(fullPluginFolderPath)

            break

    def getPluginInstanceByName(self, name: str):
        return self.pluginInfoMap.get(name, PluginInfo(None)).pluginInstance

    def refreshPluginState(self):
        for pluginName in self.availablePluginNames:
            active = self.pluginActiveStatus.get(pluginName, True)
            if active:
                try:
                    self.setPluginActive(pluginName, active)
                except Exception as e:
                    logger.error(str(e))

    def setViewerRegistry(self, viewerRegistry):
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
        return

    def addPlugin(self, pluginInfo: PluginInfo, loadingPluginNames: List[str] = None):
        pluginName = pluginInfo.pluginName

        try:
            if pluginName in (loadingPluginNames or []):
                raise RuntimeError(f'Circular dependency found when loading plugin {pluginName}: {loadingPluginNames}')
                
            loadingPluginNames.append(pluginName)
            pluginFolder = pluginInfo.pluginFolder
            logger.info(f'Importing plugin {pluginFolder}.')

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

        if infoDict == None:
            infoDict = dict()

        self.pluginActiveStatus = infoDict.get('plugin_active_status', dict())
        self.refreshPluginState()