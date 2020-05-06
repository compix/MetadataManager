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
import MDApi
from ServiceRegistry import ServiceRegistry
import viewers.resources_qrc
from MetadataManagerCore.task_processor.TaskProcessor import TaskProcessor
from MetadataManagerCore.task_processor.ActionTaskPicker import ActionTaskPicker
import time
from ConsoleApp import ConsoleApp

# Visual Scripting imports:
from VisualScriptingExtensions.ExtendedVisualScripting import ExtendedVisualScripting
from VisualScriptingExtensions.CodeGenerator import CodeGenerator
import VisualScriptingExtensions.mongodb_nodes
import VisualScriptingExtensions.document_action_nodes
import VisualScriptingExtensions.action_nodes
import VisualScriptingExtensions.versioning_nodes
import VisualScriptingExtensions.third_party_extensions.deadline_nodes
import VisualScriptingExtensions.environment_nodes

class ApplicationMode(Enum):
    GUI = 'GUI'
    Console = 'Console'

    def __str__(self):
        return self.value

class Bootstrapper(object):
    def __init__(self, mode : ApplicationMode, taskFilePath: str):
        super().__init__()
        self.mode = mode
        self.taskFilePath = taskFilePath
        self.initLogging()

        self.logger.info(f"Initializing application with mode: {mode}")

        SETTINGS = QtCore.QSettings(asset_manager.getMainSettingsPath(), QtCore.QSettings.IniFormat)

        self.appInfo = AppInfo()
        self.appInfo.company = SETTINGS.value("company")
        self.appInfo.appName = SETTINGS.value("app_name")
        self.mongodbHost = SETTINGS.value("mongodb_host")
        self.dbName = SETTINGS.value("db_name")

        self.dbManager = None
        self.serviceRegistry = ServiceRegistry()

        if self.mode == ApplicationMode.GUI:
            self.app = QApplication([])
            self.loaderWindow = LoaderWindow(self.app, self.appInfo, self.logger)
        elif self.mode == ApplicationMode.Console:
            self.consoleApp = ConsoleApp(self.appInfo, self.serviceRegistry, taskFilePath=self.taskFilePath)
        
        QThreadPool.globalInstance().start(qt_util.LambdaTask(self.initDataBaseManager))

    def run(self):
        if self.mode == ApplicationMode.GUI:
            status = self.app.exec_()
        elif self.mode == ApplicationMode.Console:
            # Wait for initialization completion:
            status = self.consoleApp.exec()
            self.logger.info("Quitting application...")
            QtCore.QThreadPool.globalInstance().waitForDone()
        if self.appInfo.initialized:
            self.save()

        return status

    def initLogging(self):
        logFilename = asset_manager.getLogFilePath()
        if not os.path.isdir(os.path.dirname(logFilename)):
            os.makedirs(os.path.dirname(logFilename))

        fileHandler = logging.FileHandler(logFilename)
        fileHandler.setLevel(logging.DEBUG)

        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.DEBUG)

        logging.basicConfig(format='%(asctime)s %(name)s:%(threadName)s %(levelname)s: %(message)s', 
                            datefmt='%H:%M:%S', handlers=[fileHandler, consoleHandler], level=logging.DEBUG)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def initDataBaseManager(self):
        connected = False
        self.dbManager = MongoDBManager(self.mongodbHost, self.dbName)

        tStart = time.time()
        timeout = None
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
            QtCore.QThreadPool.globalInstance().waitForDone()
            self.app.quit()

    def initServices(self):
        self.serviceRegistry.deadlineService = DeadlineService(None)
        self.serviceRegistry.services.append(self.serviceRegistry.deadlineService)

        self.serviceRegistry.actionManager = ActionManager()
        self.serviceRegistry.services.append(self.serviceRegistry.actionManager)
        
        self.serviceRegistry.environmentManager = EnvironmentManager()
        self.serviceRegistry.services.append(self.serviceRegistry.environmentManager)

        self.serviceRegistry.codeGenerator = CodeGenerator(self.serviceRegistry.actionManager)
        self.serviceRegistry.services.append(self.serviceRegistry.codeGenerator)

        self.serviceRegistry.dbManager = self.dbManager
        self.serviceRegistry.services.append(self.dbManager)

        visualScriptingSaveDataFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "VisualScripting_SaveData")
        self.serviceRegistry.visualScripting = ExtendedVisualScripting(visualScriptingSaveDataFolder, self.serviceRegistry.actionManager, 
                                                                       self.serviceRegistry.codeGenerator)
        self.serviceRegistry.services.append(self.serviceRegistry.visualScripting)

        self.serviceRegistry.taskProcessor = TaskProcessor()
        actionTaskPicker = ActionTaskPicker(self.serviceRegistry.actionManager, self.dbManager)
        self.serviceRegistry.taskProcessor.addTaskPicker(actionTaskPicker)
        self.serviceRegistry.services.append(self.serviceRegistry.taskProcessor)

        VisualScriptingExtensions.mongodb_nodes.DB_MANAGER = self.dbManager
        VisualScriptingExtensions.environment_nodes.ENVIRONMENT_MANAGER = self.serviceRegistry.environmentManager
        VisualScriptingExtensions.third_party_extensions.deadline_nodes.DEADLINE_SERVICE = self.serviceRegistry.deadlineService

        MDApi.ENVIRONMNET_MANAGER = self.serviceRegistry.environmentManager
        MDApi.DB_MANAGER = self.dbManager

    def onDBManagerConnected(self):
        self.initServices()
        self.load()
        self.appInfo.initialized = True

        if self.mode == ApplicationMode.GUI:
            qt_util.runInMainThread(self.loaderWindow.window.hide)
            qt_util.runInMainThread(self.setupMainWindowManager)

    def setupMainWindowManager(self):
        self.mainWindowManager = MainWindowManager(self.app, self.appInfo, self.serviceRegistry)
        self.mainWindowManager.show()

    def load(self, settings = None):
        if settings == None:
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)
        
        for service in self.serviceRegistry.services:
            try:
                service.load(settings, self.dbManager)
            except:
                pass

    def save(self, settings = None):
        self.logger.info("Saving...")
        if settings == None:
            settings = QtCore.QSettings(self.appInfo.company, self.appInfo.appName)

        for service in self.serviceRegistry.services:
            try:
                service.save(settings, self.dbManager)
            except:
                pass

        self.logger.info("Saving completed.")