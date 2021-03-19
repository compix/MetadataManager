
from typing import List
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore import Keys
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.Event import Event
from RenderingPipelinePlugin import PipelineKeys
import logging

logger = logging.getLogger(__name__)

class RenderingPipelineManager(object):
    def __init__(self, environmentManager: EnvironmentManager, dbManager: MongoDBManager) -> None:
        super().__init__()

        self.environmentManager = environmentManager
        self.dbManager = dbManager

        self.pipelines: List[RenderingPipeline] = []
        self.pipelineClasses = set()

        self.onPipelineClassRegistrationEvent = Event()

        self.registerClass(RenderingPipeline)

    def registerClass(self, pipelineClass):
        self.pipelineClasses.add(pipelineClass)
        self.load(pipelineClass.__name__)

        self.onPipelineClassRegistrationEvent(pipelineClass.__name__)

    def getPipelineFromName(self, pipelineName: str) -> RenderingPipeline:
        for pipeline in self.pipelines:
            if pipeline.name == pipelineName:
                return pipeline

        return None

    @property
    def pipelineNames(self):
        return [pipeline.name for pipeline in self.pipelines]

    @property
    def pipelineClassNames(self) -> List[str]:
        return [pipelineClass.__name__ for pipelineClass in self.pipelineClasses]

    def getPipelineClassFromName(self, className: str):
        for pipelineClass in self.pipelineClasses:
            if pipelineClass.__name__ == className:
                return pipelineClass

        return None

    def pipelineDict(self, pipeline: RenderingPipeline) -> dict:
        return {
            'name': pipeline.name,
            'className': pipeline.__class__.__name__
        }

    def constructPipelineFromDict(self, pipelineInfoDict: dict) -> RenderingPipeline:
        pipelineName = pipelineInfoDict.get('name')
        className = pipelineInfoDict.get('className')
        pipelineClass = self.getPipelineClassFromName(className)

        if pipelineClass:
            return pipelineClass(pipelineName, self.environmentManager, self.dbManager)
        else:
            logger.error(f'Could not construct pipeline from {pipelineInfoDict}')

        return None

    def constructPipeline(self, pipelineName: str, pipelineClassName: str):
        pipeline = self.constructPipelineFromDict({'name': pipelineName, 'className': pipelineClassName})
        if not pipeline:
            return None

        return pipeline

    def addNewPipeline(self, pipelineName: str, pipelineClassName: str) -> RenderingPipeline:
        pipeline = self.constructPipelineFromDict({'name': pipelineName, 'className': pipelineClassName})
        if not pipeline:
            return None

        self.addNewPipelineInstance(pipeline)

        return pipeline

    def addNewPipelineInstance(self, pipeline: RenderingPipeline):
        self.pipelines.append(pipeline)
        self.save(pipeline)

    def saveProjectSubfolders(self, subfolderDict: dict):
        renderingPipelineState = self.dbManager.db[Keys.STATE_COLLECTION].find_one({'_id': 'rendering_pipeline'})
        if not renderingPipelineState:
            renderingPipelineState = dict()

        renderingPipelineState['project_subolders'] = subfolderDict
        self.dbManager.db[Keys.STATE_COLLECTION].replace_one({'_id': 'rendering_pipeline'}, renderingPipelineState, upsert=True)

    def loadProjectSubfolderDict(self):
        renderingPipelineState = self.dbManager.db[Keys.STATE_COLLECTION].find_one({'_id': 'rendering_pipeline'})
        projectSubfolderDict = None
        if renderingPipelineState:
            projectSubfolderDict = renderingPipelineState.get('project_subolders')

        if not projectSubfolderDict:
            projectSubfolderDict = {
                PipelineKeys.RenderScenesFolder: 'scenes/render',
                PipelineKeys.InputScenesFolder: 'scenes/input',
                PipelineKeys.EnvironmentScenesFolder: 'scenes/environment',
                PipelineKeys.NukeScenesFolder: 'scenes/nuke',
                PipelineKeys.RenderingsFolder: 'renderings/autogen',
                PipelineKeys.PostFolder: 'post/autogen',
                PipelineKeys.DeliveryFolder: 'delivery'
            }

        return projectSubfolderDict

    def save(self, pipeline: RenderingPipeline):
        renderingPipelineState = self.dbManager.db[Keys.STATE_COLLECTION].find_one({'_id': 'rendering_pipeline'})
        if not renderingPipelineState:
            renderingPipelineState = dict()

        pipelinesDict = renderingPipelineState.setdefault('pipelines', dict())
        pipelinesDict[pipeline.name] = self.pipelineDict(pipeline)

        self.dbManager.db[Keys.STATE_COLLECTION].replace_one({'_id': 'rendering_pipeline'}, renderingPipelineState, upsert=True)

    def load(self, pipelineClassName: str):
        # Note that rendering pipeline classes must be registered/known at this point:
        renderingPipelineState = self.dbManager.db[Keys.STATE_COLLECTION].find_one({'_id': 'rendering_pipeline'})
        if renderingPipelineState:
            renderingPipelineDicts = renderingPipelineState.get('pipelines', {})

            for pipelineInfoDict in renderingPipelineDicts.values():
                if pipelineInfoDict.get('className') == pipelineClassName:
                    pipeline = self.constructPipelineFromDict(pipelineInfoDict)
                    if pipeline:
                        self.pipelines.append(pipeline)