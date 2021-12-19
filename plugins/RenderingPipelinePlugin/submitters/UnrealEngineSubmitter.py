from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import SubmitterPipelineKeyRequirementsResponse
from RenderingPipelinePlugin.unreal_engine import UnrealEnginePipelineKeys
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os

def createUnrealEnginePipelinePluginInfoDictionaryFromSettings(settings: dict):
    project = settings.get(UnrealEnginePipelineKeys.ProjectFilename)
    queueSettings = settings.get(UnrealEnginePipelineKeys.MoviePipelineQueueSettings)
    
    pluginInfoDict = deadline_nodes.createUnrealEnginePipelinePluginInfoDictionary(
        project, 
        queueSettings, 
        VSyncEnabled=settings.get(UnrealEnginePipelineKeys.VSync),
        OverrideResolution=settings.get(UnrealEnginePipelineKeys.OverrideWindowResolution),
        ResX=settings.get(UnrealEnginePipelineKeys.WindowResolutionX),
        ResY=settings.get(UnrealEnginePipelineKeys.WindowResolutionY))

    return pluginInfoDict

class UnrealEngineInputSceneCreationSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getUnrealEnginePipelinePluginName()
        jobName = self.pipeline.namingConvention.getInputSceneName(documentWithSettings)
        batchName = 'Input Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 4,
                                                   documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getCreatedInputSceneFilename(documentWithSettings)
        projectFolder = os.path.dirname(documentWithSettings.get(UnrealEnginePipelineKeys.ProjectFilename))
        jobInfoDict['OutputDirectory0'] = os.path.join(projectFolder, filename.replace('/Game', '/Content', 1))
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneCreationInfo)

        extraPluginInfoDict = createUnrealEnginePipelinePluginInfoDictionaryFromSettings(documentWithSettings)

        return deadline_nodes.submitUnrealEngineScriptJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                          unrealEngineVersion=documentWithSettings.get(PipelineKeys.UnrealEngineVersion), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.InputSceneCreationScript, 
                                                        messages=['An input scene creation script is not specified.'], isFile=True)

class UnrealEngineRenderSceneCreationSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getUnrealEnginePipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderSceneName(documentWithSettings)
        batchName = 'Render Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 3, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        projectFolder = os.path.dirname(documentWithSettings.get(UnrealEnginePipelineKeys.ProjectFilename))
        jobInfoDict['OutputDirectory0'] = os.path.join(projectFolder, filename.replace('/Game', '/Content', 1))
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')
        pipelineInfoDict[PipelineKeys.Frames] = frames

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneCreationInfo)

        extraPluginInfoDict = createUnrealEnginePipelinePluginInfoDictionaryFromSettings(documentWithSettings)

        return deadline_nodes.submitUnrealEngineScriptJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                            unrealEngineVersion=documentWithSettings.get(PipelineKeys.RenderSceneCreationScript), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderSceneCreationScript, 
                                                        messages=['A render scene creation script is not specified.'], isFile=True)

class UnrealEngineRenderingSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.getUnrealEnginePipelinePluginName()
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
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderingInfo)

        extraPluginInfoDict = createUnrealEnginePipelinePluginInfoDictionaryFromSettings(documentWithSettings)
        extraPluginInfoDict["Map"] = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)

        pipelineInfoDict = documentWithSettings
        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')
        pipelineInfoDict[PipelineKeys.Frames] = frames

        return deadline_nodes.submitUnrealEngineRenderJob(pipelineInfoDict, jobInfoDict, 
                                                          unrealEngineVersion=documentWithSettings.get(PipelineKeys.UnrealEngineVersion), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.RenderingNaming, 
                perspectiveDependent=True, messages=['Rendering naming convention not specified.'])