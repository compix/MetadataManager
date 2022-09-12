from MetadataManagerCore import Keys
from MetadataManagerCore.task_processor.Task import Task
from MetadataManagerCore.actions.ActionManager import ActionManager
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager
import logging

logger = logging.getLogger(__name__)

class PipelineDocumentActionTask(Task):
    def __init__(self, actionManager: ActionManager, pipelineManager: RenderingPipelineManager):
        super().__init__()

        self.actionManager = actionManager
        self.pipelineManager = pipelineManager

    def getEntryVerified(self, dataDict, key):
        value = dataDict.get(key)
        if value == None:
            raise RuntimeError(f"The data dictionary is missing the key: {key}")
        
        return value

    def execute(self, dataDict: dict):
        submittedData = dataDict.get('submittedData')
        collectionName = self.getEntryVerified(submittedData, Keys.collection)
        pipeline = self.pipelineManager.getPipelineFromCollectionName(collectionName)
        if not pipeline:
            raise RuntimeError(f'Could not find pipeline for collection {collectionName}')

        logger.info(f'Activating pipeline {pipeline.name}')
        pipeline.activate()

        actionId = self.getEntryVerified(dataDict, 'actionId')

        action = self.actionManager.getActionById(actionId)
        if action is None:
            raise RuntimeError(f'Unknown actionId: {actionId}')

        logger.info(f'Running action {action.displayName} with id {action.id}')

        action.execute(submittedData)