
from viewers.ViewerRegistry import ViewerRegistry
from AppInfo import AppInfo
from typing import List
from MetadataManagerCore.mongodb_manager import MongoDBManager
from MetadataManagerCore import Keys
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.Event import Event
from RenderingPipelinePlugin import PipelineKeys
import logging
from ServiceRegistry import ServiceRegistry

logger = logging.getLogger(__name__)

RenderingPipelinesCollectionName = 'rendering_pipelines'

class RenderingPipelineManager(object):
    def __init__(self, serviceRegistry: ServiceRegistry, viewerRegistry: ViewerRegistry, appInfo: AppInfo) -> None:
        super().__init__()

        self.appInfo = appInfo
        self.serviceRegistry = serviceRegistry
        self.viewerRegistry = viewerRegistry
        self.environmentManager = serviceRegistry.environmentManager
        self.dbManager = serviceRegistry.dbManager

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
            'className': pipeline.__class__.__name__,
            'customData': pipeline.customData
        }

    def constructPipelineFromDict(self, pipelineInfoDict: dict) -> RenderingPipeline:
        pipelineName = pipelineInfoDict.get('name')
        className = pipelineInfoDict.get('className')
        pipelineClass = self.getPipelineClassFromName(className)

        if pipelineClass:
            pipeline = pipelineClass(pipelineName, self.serviceRegistry, self.viewerRegistry, self.appInfo)
            pipeline.customData = pipelineInfoDict.get('customData')
            return pipeline
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

    def addNewPipelineInstance(self, pipeline: RenderingPipeline, replaceExisting=True):
        existingPipeline = self.getPipelineFromName(pipeline.name)

        addPipeline = True
        if existingPipeline:
            if replaceExisting:
                self.pipelines.remove(existingPipeline)
                addPipeline = True
            else:
                addPipeline = False

        if addPipeline:
            self.pipelines.append(pipeline)
            self.save(pipeline)

    def save(self, pipeline: RenderingPipeline):
        collection = self.dbManager.db[RenderingPipelinesCollectionName]
        collection.replace_one({'_id': pipeline.name}, self.pipelineDict(pipeline), upsert=True)

    def load(self, pipelineClassName: str):
        # Note that rendering pipeline classes must be registered/known at this point:
        collection = self.dbManager.db[RenderingPipelinesCollectionName]
        if collection:
            for pipelineInfoDict in collection.find({}):
                if pipelineInfoDict.get('className') == pipelineClassName:
                    pipeline = self.constructPipelineFromDict(pipelineInfoDict)
                    if pipeline:
                        self.pipelines.append(pipeline)

    def deletePipeline(self, pipelineName: str):
        pipeline = self.getPipelineFromName(pipelineName)
        if pipeline:
            if pipeline.environment:
                self.environmentManager.archive(self.dbManager, pipeline.environment)

            # Collections may not exist:
            try:
                self.serviceRegistry.dbManager.dropCollection(pipeline.dbCollectionName)
                self.serviceRegistry.dbManager.dropCollection(pipeline.dbCollectionName + Keys.OLD_VERSIONS_COLLECTION_SUFFIX)
            except:
                pass
            self.pipelines.remove(pipeline)
            self.dbManager.db[RenderingPipelinesCollectionName].delete_one({'_id': pipelineName})