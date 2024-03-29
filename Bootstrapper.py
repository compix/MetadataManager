from MetadataManagerCore import config
from plugin.PluginManager import PluginManager
from ApplicationMode import ApplicationMode
from updater.Updater import Updater
from MetadataManagerCore.host.HostProcessController import HostProcessController
from MetadataManagerCore.file.FileHandlerManager import FileHandlerManager
from MetadataManagerCore.service.WatchDogService import WatchDogService
from MetadataManagerCore.service.ServiceManager import ServiceManager
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager
from PySide2.QtCore import QThreadPool
from PySide2 import QtCore
from PySide2.QtWidgets import QApplication
import asset_manager
from qt_extensions import qt_util
from MetadataManagerCore.mongodb_manager import MongoDBManager
from time import sleep
from datetime import datetime
import logging
from enum import Enum
from LoaderWindow import LoaderWindow
from AppInfo import AppInfo
from MainWindowManager import MainWindowManager
import os
import sys
from MetadataManagerCore.third_party_integrations.deadline.deadline_service import DeadlineService, DeadlineServiceInfo
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from ServiceRegistry import ServiceRegistry

# Do not remove the resources_qrc import. It loads the custom resources/icons for Qt.
import resources_qrc
from MetadataManagerCore.task_processor.TaskProcessor import TaskProcessor
from MetadataManagerCore.task_processor.ActionTaskPicker import ActionTaskPicker
import time
from ConsoleApp import ConsoleApp
from MetadataManagerCore.file.PrintFileHandler import PrintFileHandler

# Keep the following imports to ensure plugins have access to the modules.
import MetadataManagerCore.communication.messaging

# Visual Scripting imports:
from VisualScriptingExtensions.ExtendedVisualScripting import ExtendedVisualScripting
from VisualScriptingExtensions.CodeGenerator import CodeGenerator
import VisualScriptingExtensions.mongodb_nodes
import VisualScriptingExtensions.document_action_nodes
import VisualScriptingExtensions.action_nodes
import VisualScriptingExtensions.versioning_nodes
import VisualScriptingExtensions.third_party_extensions.deadline_nodes
import VisualScriptingExtensions.third_party_extensions.photoshop_nodes
import VisualScriptingExtensions.environment_nodes

class Bootstrapper(object):
    def __init__(self, mode : ApplicationMode, taskFilePath: str, launcherFilename: str, loggerLevel: str = None):
        super().__init__()
        self.mode = mode
        self.taskFilePath = taskFilePath
        self.launcherFilename = launcherFilename
        self.initLogging(loggerLevel)

        self.logger.info(f"Initializing application with mode: {mode} and launcher: {launcherFilename}")

        SETTINGS = QtCore.QSettings(asset_manager.getMainSettingsPath(), QtCore.QSettings.IniFormat)
        
        config.RABBIT_MQ_HOST = SETTINGS.value("rabbit_mq_host")
        config.RABBIT_MQ_USERNAME = SETTINGS.value("rabbit_mq_username")
        config.RABBIT_MQ_PASSWORD = SETTINGS.value("rabbit_mq_password")

        self.appInfo = AppInfo()
        self.appInfo.company = SETTINGS.value("company")
        self.appInfo.appName = SETTINGS.value("app_name")
        self.appInfo.mode = mode
        self.mongodbHost = SETTINGS.value("mongodb_host")
        self.dbName = SETTINGS.value("db_name")
        self.hostProcessController = None
        self.serviceManager = None
        self.dbManager = None
        self.serviceRegistry = ServiceRegistry()
        self.serviceRegistry.appInfo = self.appInfo

        self.restartRequested = False
        self.updater = None

        dbInitTimeout = None
        if self.mode == ApplicationMode.GUI:
            self.app = QApplication([])
            self.app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
            self.loaderWindow = LoaderWindow(self.app, self.appInfo, self.logger, self)
        elif self.mode == ApplicationMode.Console:
            dbInitTimeout = 60.0
            self.consoleApp = ConsoleApp(self.appInfo, self.serviceRegistry, taskFilePath=self.taskFilePath, initTimeout = 240.0)
        
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.initDataBaseManager, dbInitTimeout))

    def requestRestart(self):
        self.restartRequested = True
        self.mainWindowManager.close()

    def run(self):
        if self.mode == ApplicationMode.GUI:
            status = self.app.exec_()
        elif self.mode == ApplicationMode.Console:
            # Wait for initialization completion:
            status = self.consoleApp.exec()
            self.logger.info("Quitting application...")
            self.shutdown()
        else:
            status = None
            self.logger.error(f'Unknown Mode: {self.mode}')

        return status

    def shutdown(self):
        for service in self.serviceRegistry.services:
            try:
                service.shutdown
                hasShutdownFunction = True
            except:
                hasShutdownFunction = False

            if hasShutdownFunction:                
                service.shutdown()

        if self.updater:
            self.updater.shutdown()

        if self.appInfo.initialized:
            self.save()

        self.dbManager.disconnect()

        QtCore.QThreadPool.globalInstance().waitForDone()

    def initLogging(self, loggerLevel: str):
        logFilename = asset_manager.getLogFilePath()
        if not os.path.isdir(os.path.dirname(logFilename)):
            os.makedirs(os.path.dirname(logFilename))

        strToLoggerLevel = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }

        if loggerLevel:
            loggerLevel = strToLoggerLevel.get(loggerLevel.lower())

        if not loggerLevel:
            loggerLevel = logging.INFO

        fileHandler = logging.FileHandler(logFilename)
        fileHandler.setLevel(loggerLevel)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(loggerLevel)

        logging.basicConfig(format='%(asctime)s %(name)s:%(threadName)s %(levelname)s: %(message)s', 
                            datefmt='%H:%M:%S', handlers=[fileHandler, consoleHandler], level=logging.DEBUG)

        self.logger = logging.getLogger(__name__)

    def initDataBaseManager(self, timeout=None):
        connected = False
        self.dbManager = MongoDBManager(self.mongodbHost, self.dbName)

        tStart = time.time()
        while not connected and (timeout == None or time.time() - tStart < timeout) and not self.appInfo.applicationQuitting:
            self.logger.info("Connecting to database...")

            try:
                self.dbManager.connect()
                self.logger.info("Connected.")
                connected = True
            except Exception as e:
                if self.appInfo.applicationQuitting:
                    return

                print(f"Error: {str(e)}")
                sleep(2)
                self.logger.info("Failed to connect. Retrying...")
                sleep(1)
                continue

        if not connected:
            qt_util.runInMainThread(self.onDBManagerConnectionTimeout)
            return
        
        self.onDBManagerConnected()

    def onDBManagerConnectionTimeout(self):
        if self.app:
            self.shutdown()
            self.app.quit()

    def initServices(self):
        self.serviceRegistry.deadlineService = DeadlineService(None)
        self.serviceRegistry.services.append(self.serviceRegistry.deadlineService)

        self.serviceRegistry.actionManager = ActionManager()
        self.serviceRegistry.services.append(self.serviceRegistry.actionManager)
        
        self.serviceRegistry.environmentManager = EnvironmentManager()
        self.serviceRegistry.services.append(self.serviceRegistry.environmentManager)

        self.serviceRegistry.dbManager = self.dbManager
        self.serviceRegistry.services.append(self.dbManager)

        self.serviceRegistry.documentFilterManager = DocumentFilterManager(self.serviceRegistry.dbManager)
        self.serviceRegistry.services.append(self.serviceRegistry.documentFilterManager)

        self.serviceRegistry.codeGenerator = CodeGenerator(self.serviceRegistry.actionManager, self.serviceRegistry.documentFilterManager)
        self.serviceRegistry.services.append(self.serviceRegistry.codeGenerator)

        self.serviceRegistry.taskProcessor = TaskProcessor()
        actionTaskPicker = ActionTaskPicker(self.serviceRegistry.actionManager, self.serviceRegistry.documentFilterManager)
        self.serviceRegistry.taskProcessor.addTaskPicker(actionTaskPicker)
        self.serviceRegistry.services.append(self.serviceRegistry.taskProcessor)

        VisualScriptingExtensions.mongodb_nodes.DB_MANAGER = self.dbManager
        VisualScriptingExtensions.environment_nodes.ENVIRONMENT_MANAGER = self.serviceRegistry.environmentManager
        VisualScriptingExtensions.third_party_extensions.deadline_nodes.DEADLINE_SERVICE = self.serviceRegistry.deadlineService

        self.serviceManager = ServiceManager(self.dbManager, self.hostProcessController, self.serviceRegistry, self.mode == ApplicationMode.Console)
        self.serviceRegistry.serviceManager = self.serviceManager
        self.serviceRegistry.services.append(self.serviceManager)
        self.serviceManager.registerServiceClass(WatchDogService)

        self.fileHandlerManager = FileHandlerManager()
        self.serviceRegistry.fileHandlerManager = self.fileHandlerManager
        self.serviceRegistry.services.append(self.fileHandlerManager)

        pluginFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")
        privatePluginFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "private", "plugins")
        self.serviceRegistry.pluginManager = PluginManager([pluginFolder, privatePluginFolder], self.serviceRegistry, self.appInfo)
        self.serviceRegistry.services.append(self.serviceRegistry.pluginManager)

        visualScriptingSaveDataFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "VisualScripting_SaveData")
        visualScriptingPrivateSaveDataFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "private", "VisualScripting_SaveData")
        self.serviceRegistry.visualScripting = ExtendedVisualScripting([visualScriptingSaveDataFolder, visualScriptingPrivateSaveDataFolder], self.serviceRegistry.actionManager, 
                                                                       self.serviceRegistry.documentFilterManager,
                                                                       self.serviceRegistry.codeGenerator)
        self.serviceRegistry.services.append(self.serviceRegistry.visualScripting)

    def onDBManagerConnected(self):
        self.initHostProcessController()

        self.initServices()
        self.load()
        self.appInfo.initialized = True

        if self.mode == ApplicationMode.GUI:
            qt_util.runInMainThread(self.loaderWindow.hide)
            qt_util.runInMainThread(self.setupMainWindowManager)
            qt_util.runInMainThread(self.setupUpdater)
    
    def setupUpdater(self):
        self.updater = Updater(self.launcherFilename, self, self.mainWindowManager.window) if self.launcherFilename else None

    def initHostProcessController(self):
        self.hostProcessController = HostProcessController(self.dbManager)
        self.hostProcessController.thisHost.onRequestedApplicationClose.subscribe(self.onRequestedApplicationClose)
        self.serviceRegistry.hostProcessController = self.hostProcessController
        self.serviceRegistry.services.append(self.hostProcessController)
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.hostProcessController.run))

    def onRequestedApplicationClose(self):
        if self.mainWindowManager:
            qt_util.runInMainThread(self.mainWindowManager.close)

    def setupMainWindowManager(self):
        self.mainWindowManager = MainWindowManager(self.app, self.appInfo, self.serviceRegistry, self)
        self.serviceRegistry.mainWindowManager = self.mainWindowManager
        
        settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)
        self.serviceRegistry.pluginManager.load(settings, self.dbManager)
        self.mainWindowManager.pluginManagerViewer.loadPluginsFolders()
        self.serviceRegistry.visualScripting.load(settings, self.dbManager)

        self.mainWindowManager.show()

    def load(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)
        
        for service in self.serviceRegistry.services:
            # Skip PluginManager if in GUI mode. It will be loaded after the main window manager is initialized.
            if self.mode == ApplicationMode.GUI:
                if isinstance(service, PluginManager):
                    continue

                if isinstance(service, ExtendedVisualScripting):
                    continue

            try:
                service.load
                hasLoadFunc = True
            except:
                hasLoadFunc = False

            if hasLoadFunc:
                service.load(settings, self.dbManager)

    def save(self, settings = None):
        if self.appInfo.mode == ApplicationMode.Console:
            return
            
        self.logger.info("Saving...")
        if settings == None:
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)

        for service in self.serviceRegistry.services:
            try:
                service.save
                hasSaveFunc = True
            except:
                hasSaveFunc = False

            if hasSaveFunc:                
                service.save(settings, self.dbManager)

        self.logger.info("Saving completed.")