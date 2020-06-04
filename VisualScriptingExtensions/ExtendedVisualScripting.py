from VisualScripting.VisualScripting import VisualScripting
import sys
import os
import importlib
from MetadataManagerCore.actions.ActionManager import ActionManager
import logging

class ExtendedVisualScripting(VisualScripting):
    def __init__(self, graphSerializationFolders, actionManager : ActionManager, codeGenerator=None):
        super().__init__(graphSerializationFolders, codeGenerator)
        self.logger = logging.getLogger(__name__)

        self.actionManager = actionManager
        self.registerVSActions()

    def registerVSActions(self):
        allGraphSettings = self.graphManager.retrieveAvailableGraphSettings()

        for graphSettings in allGraphSettings:
            moduleName = self.graphManager.getModuleNameFromGraphName(graphSettings.name)
            pythonFile = self.graphManager.getPythonCodePath(graphSettings)
            pathonFileDir = os.path.dirname(pythonFile)

            if not pathonFileDir in sys.path:
                sys.path.append(pathonFileDir)

            try:
                execModule = importlib.import_module(moduleName)
                importlib.reload(execModule)
            except Exception as e:
                self.logger.error(f'Failed to import {moduleName}. Reason: {str(e)}')
            
            try:
                docAction = execModule.ActionVS()
                try:
                    self.actionManager.registerAction(docAction)
                except Exception as e:
                    self.logger.error(f"Failed to register action {docAction.id}. Reason: {str(e)}")
            except:
                pass

