from ServiceRegistry import ServiceRegistry
from AppInfo import AppInfo
import time
import logging

class ConsoleApp(object):
    def __init__(self, appInfo: AppInfo, serviceRegistry: ServiceRegistry, taskFilePath=None, initTimeout = 10.0):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.appInfo = appInfo
        self.serviceRegistry = serviceRegistry
        self.taskFilePath = taskFilePath
        self.initTimeout = initTimeout

    def exec(self):
        tStart = time.time()
        # Wait for initialization completion:
        while not self.appInfo.initialized and not self.appInfo.applicationQuitting:
            if self.initTimeout and (time.time() - tStart > self.initTimeout):
                self.logger.error('Timeout.')
                self.appInfo.applicationQuitting = True
                return 1

        if self.appInfo.initialized:
            if self.taskFilePath:
                self.serviceRegistry.taskProcessor.processTaskFromJsonFile(self.taskFilePath)
            else:
                self.logger.warn("Please provide a task when starting in console mode.")
        else:
            if self.taskFilePath:
                self.logger.error(f'Failed to process task because the application was terminated before initialization completion: {self.taskFilePath}')
                return 1


        return 0
