from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.NamingConvention import NamingConvention
from RenderingPipelinePlugin.submitters.Submitter import Submitter
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from typing import List
import os

class BlenderSubmitter(Submitter):
    def submitInputSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None) -> str:
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.InputSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getBlenderPipelinePluginName()
        jobName = self.pipeline.namingConvention.getInputSceneName(documentWithSettings)
        batchName = 'Input Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.getInputSceneCreationPriority(documentWithSettings),
                                                   documentWithSettings.get(PipelineKeys.DeadlineInputScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getCreatedInputSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineInputSceneTimeout)

        extraPluginInfoDict = {
            "BaseScene": self.pipeline.namingConvention.getBaseSceneFilename(documentWithSettings)
        }

        return deadline_nodes.submitBlenderPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                       blenderVersion=documentWithSettings.get(PipelineKeys.BlenderVersion), extraPluginInfoDict=extraPluginInfoDict)

    def submitRenderSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        sceneCreationScript = documentWithSettings.get(PipelineKeys.RenderSceneCreationScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getBlenderPipelinePluginName()
        jobName = self.pipeline.namingConvention.getRenderSceneName(documentWithSettings)
        batchName = 'Render Scene'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.getRenderSceneCreationPriority(documentWithSettings), 
                                                   documentWithSettings.get(PipelineKeys.DeadlineRenderScenePool), dependentJobIds=dependentJobIds)

        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        jobInfoDict['OutputDirectory0'] = os.path.dirname(filename)
        jobInfoDict['OutputFilename0'] = os.path.basename(filename)

        # Make sure the output folder exists:
        os.makedirs(jobInfoDict['OutputDirectory0'], exist_ok=True)

        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')
        pipelineInfoDict[PipelineKeys.Frames] = frames

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineRenderSceneTimeout)

        extraPluginInfoDict = {
            "BaseScene": self.pipeline.namingConvention.getBaseSceneFilename(documentWithSettings) if documentWithSettings.get(PipelineKeys.BaseSceneNaming) else ''
        }

        return deadline_nodes.submitBlenderPipelineJob(sceneCreationScript, pipelineInfoDict, jobInfoDict, 
                                                       blenderVersion=documentWithSettings.get(PipelineKeys.BlenderVersion), extraPluginInfoDict=extraPluginInfoDict)

    def submitRendering(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.getBlenderPluginName()
        jobName = self.pipeline.namingConvention.getRenderingName(documentWithSettings)
        batchName = 'Rendering'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.getRenderingPriority(documentWithSettings), 
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
        pluginInfoDict = deadline_nodes.createBlenderPluginInfoDictionary(sceneFilename, os.path.splitext(filename)[0])

        return deadline_nodes.submitJob(jobInfoDict, pluginInfoDict)