from RenderingPipelinePlugin.NamingConvention import replaceGermanCharacters
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
from MetadataManagerCore.actions.DocumentAction import DocumentAction
import os
import typing
import logging

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class Submitter(object):
    def __init__(self, pipeline: 'RenderingPipeline') -> None:
        super().__init__()

        self.pipeline = pipeline

    @property
    def baseDeadlinePriority(self):
        priority = self.pipeline.environmentSettings.get(PipelineKeys.DeadlinePriority)
        if priority != None:
            return int(priority)

        return 50

    def createJobInfoDictionary(self, pluginName: str, name: str, batchName: str, priority: int, pool: str, dependentJobIds: List[str]=None):
        d = {"Plugin": pluginName, 
             "Name": replaceGermanCharacters(name),
             "BatchName": replaceGermanCharacters(f'{self.pipeline.name} {batchName}'), 
             "Priority": priority, 
             "Department":"", 
             "Pool":pool, 
             "SecondaryPool":"",
             "Group":""}

        if dependentJobIds:
            d["JobDependencies"] = (",".join(dependentJobIds) if isinstance(dependentJobIds, list) else dependentJobIds)

        return d

    def setTimeout(self, jobInfoDict: dict, documentWithSettings: dict, timeoutKey: str):
        timeout = documentWithSettings.get(timeoutKey)
        if timeout != None and timeout.strip() != '':
            try:
                jobInfoDict['TaskTimeoutMinutes'] = int(timeout)
            except Exception as e:
                logger.error(str(e))

    def getInputSceneCreationPriority(self, documentWithSettings: dict):
        return documentWithSettings.get(PipelineKeys.DeadlinePriority, self.baseDeadlinePriority) + 4

    def getrenderSceneCreationPriority(self, documentWithSettings: dict):
        return documentWithSettings.get(PipelineKeys.DeadlinePriority, self.baseDeadlinePriority) + 3

    def getRenderingPriority(self, documentWithSettings: dict):
        return documentWithSettings.get(PipelineKeys.DeadlinePriority, self.baseDeadlinePriority) + 2

    def getNukePriority(self, documentWithSettings: dict):
        return documentWithSettings.get(PipelineKeys.DeadlinePriority, self.baseDeadlinePriority) + 1

    def getDeliveryPriority(self, documentWithSettings: dict):
        return documentWithSettings.get(PipelineKeys.DeadlinePriority, self.baseDeadlinePriority)

    def submitInputSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitRenderSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitRendering(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitNuke(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.getNukePluginName()
        jobName = self.pipeline.namingConvention.getPostName(documentWithSettings)
        batchName = 'Post'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.getNukePriority(documentWithSettings), 
                                                   documentWithSettings.get(PipelineKeys.DeadlineNukePool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getPostFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, ext in enumerate(RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)):
            filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            jobInfoDict[f'OutputDirectory{i}'] = os.path.dirname(filename)
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineNukeTimeout)

        sceneFilename = self.pipeline.namingConvention.getNukeSceneFilename(documentWithSettings)
        scriptFilename = documentWithSettings.get(PipelineKeys.NukeScript)

        pluginInfoDict = deadline_nodes.createNukePluginInfoDictionary(sceneFilename, version=documentWithSettings.get(PipelineKeys.NukeVersion))
        scriptInfoDict = documentWithSettings

        return deadline_nodes.submitNukeJob(jobInfoDict, pluginInfoDict, scriptFilename, scriptInfoDict, jobDependencies=dependentJobIds)

    def submitCopyForDelivery(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pluginName = deadline_nodes.getMetadataManagerPluginName()
        jobName = self.pipeline.namingConvention.getDeliveryName(documentWithSettings)
        batchName = 'Delivery Copy'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.getDeliveryPriority(documentWithSettings), 
                                                   documentWithSettings.get(PipelineKeys.DeadlineDeliveryPool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, ext in enumerate(RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)):
            filename = self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings, ext=ext)
            jobInfoDict[f'OutputDirectory{i}'] = os.path.dirname(filename)
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineDeliveryTimeout)

        actionId = f'{self.pipeline.name}_CopyForDeliveryDocumentAction'

        taskInfoDict = deadline_nodes.createMetadataManagerActionTaskDictForDocument(actionId=actionId, document=documentWithSettings, collections=[self.pipeline.dbCollectionName])

        return deadline_nodes.submitMetadataManagerJob(taskInfoDict, jobInfoDict, jobDependencies=dependentJobIds)