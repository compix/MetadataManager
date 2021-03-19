from RenderingPipelinePlugin.NamingConvention import replaceGermanCharacters
from RenderingPipelinePlugin import PipelineKeys
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
from MetadataManagerCore.actions.DocumentAction import DocumentAction
import os
import typing

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
        return {"Plugin": pluginName, 
                "Name": replaceGermanCharacters(name),
                "BatchName": replaceGermanCharacters(f'{self.pipeline.name} {batchName}'), 
                "Priority": priority, 
                "Department":"", 
                "Pool":pool, 
                "SecondaryPool":"",
                "Group":"",
                "JobDependencies":(",".join(dependentJobIds) if isinstance(dependentJobIds, list) else dependentJobIds)}

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
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Post'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority, documentWithSettings.get(PipelineKeys.DeadlineNukePool), dependentJobIds=dependentJobIds)

        sceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        scriptFilename = documentWithSettings.get(PipelineKeys.NukeScript)

        pluginInfoDict = deadline_nodes.createNukePluginInfoDictionary(sceneFilename, version=documentWithSettings.get(PipelineKeys.NukeVersion))
        scriptInfoDict = documentWithSettings

        return deadline_nodes.submitNukeJob(jobInfoDict, pluginInfoDict, scriptFilename, scriptInfoDict, jobDependencies=dependentJobIds)

    def submitCopyForDelivery(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pluginName = deadline_nodes.getMetadataManagerPluginName()
        jobName = self.pipeline.namingConvention.getDeliveryName(documentWithSettings)
        batchName = 'Delivery Copy'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority, documentWithSettings.get(PipelineKeys.DeadlineDeliveryPool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings, ext=self.pipeline.getPreferredPreviewExtension(documentWithSettings))
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        actionId = f'{self.pipeline.name}_CopyForDeliveryDocumentAction'

        taskInfoDict = deadline_nodes.createMetadataManagerActionTaskDictForDocument(actionId=actionId, document=documentWithSettings, collections=[self.pipeline.dbCollectionName])

        return deadline_nodes.submitMetadataManagerJob(taskInfoDict, jobInfoDict, jobDependencies=dependentJobIds)