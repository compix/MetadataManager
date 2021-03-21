from RenderingPipelinePlugin.submitters.Submitter import Submitter
from RenderingPipelinePlugin import PipelineKeys
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os

class Max3dsSubmitter(Submitter):
    def submitInputSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        self.pipeline.namingConvention.addFilenameInfo(documentWithSettings)
        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Input Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority, documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getInputSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    def submitRenderSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        self.pipeline.namingConvention.addFilenameInfo(documentWithSettings)
        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Render Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority, documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    def submitRendering(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.get3dsMaxPluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Rendering'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority, documentWithSettings.get(PipelineKeys.DeadlineRenderingPool), dependentJobIds=dependentJobIds)
        filename = self.pipeline.namingConvention.getRenderingFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)
        
        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingTimeout)

        sceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        pluginInfoDict = deadline_nodes.create3dsMaxPluginInfoDictionary(sceneFilename, Version=documentWithSettings.get(PipelineKeys.Max3dsVersion))

        return deadline_nodes.submitJob(jobInfoDict, pluginInfoDict)