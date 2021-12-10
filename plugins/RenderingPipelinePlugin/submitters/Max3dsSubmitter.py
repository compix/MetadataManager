from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import Submitter, SubmitterPipelineKeyRequirementsResponse
from RenderingPipelinePlugin import PipelineKeys
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os

class Max3dsInputSceneCreationSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getInputSceneName(documentWithSettings)
        batchName = 'Input Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 4,
                                                   documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getCreatedInputSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.InputSceneCreationScript, messages=['An input scene creation script is not specified.'])

class Max3dsRenderSceneCreationSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.get3dsMaxPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderSceneName(documentWithSettings)
        batchName = 'Render Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 3, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)

        return deadline_nodes.submit_3dsMaxPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, documentWithSettings.get(PipelineKeys.Max3dsVersion))

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderSceneCreationScript, messages=['A render scene creation script is not specified.'])

class Max3dsRenderingSubmitter(RenderingPipelineSubmitter):
    def __init__(self, pipeline) -> None:
        super().__init__(pipeline)

        self.active = True
        
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.get3dsMaxPluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Rendering'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 2, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderingPool), dependentJobIds=dependentJobIds)
                                                   
        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')                                                   
        if frames:
            jobInfoDict['Frames'] = frames

        filename = self.pipeline.namingConvention.getRenderingFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)
        
        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingTimeout)

        sceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        pluginInfoDict = deadline_nodes.create3dsMaxPluginInfoDictionary(sceneFilename, Version=documentWithSettings.get(PipelineKeys.Max3dsVersion))

        return deadline_nodes.submitJob(jobInfoDict, pluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderingNaming, perspectiveDependent=True, messages=['Rendering naming convention not specified.'])