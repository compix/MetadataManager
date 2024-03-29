from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import SubmitterPipelineKeyRequirementsResponse
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os

class BlenderInputSceneCreationSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getBlenderPipelinePluginName()
        jobName = self.pipeline.namingConvention.getInputSceneName(documentWithSettings)
        batchName = 'Input Scene'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 4,
                                                   documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getCreatedInputSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneCreationInfo)

        extraPluginInfoDict = {
            "BaseScene": self.pipeline.namingConvention.getBaseSceneFilename(documentWithSettings)
        }

        return deadline_nodes.submitBlenderPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                       blenderVersion=documentWithSettings.get(PipelineKeys.BlenderVersion), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.InputSceneCreationScript, 
                                                        messages=['An input scene creation script is not specified.'], isFile=True)

class BlenderRenderSceneCreationSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getBlenderPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderSceneName(documentWithSettings)
        batchName = 'Render Scene'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 3, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')
        pipelineInfoDict[PipelineKeys.Frames] = frames

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneCreationInfo)

        extraPluginInfoDict = {
            "BaseScene": self.pipeline.namingConvention.getBaseSceneFilename(documentWithSettings) if documentWithSettings.get(PipelineKeys.BaseSceneNaming) else ''
        }

        return deadline_nodes.submitBlenderPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                       blenderVersion=documentWithSettings.get(PipelineKeys.BlenderVersion), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderSceneCreationScript, 
                                                        messages=['A render scene creation script is not specified.'], isFile=True)

class BlenderRenderingSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.getBlenderPluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Rendering'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 2, 
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
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingInfo)

        sceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        pluginInfoDict = deadline_nodes.createBlenderPluginInfoDictionary(sceneFilename, os.path.splitext(filename)[0])

        return deadline_nodes.submitJob(jobInfoDict, pluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderingNaming, 
                perspectiveDependent=True, messages=['Rendering naming convention not specified.'])