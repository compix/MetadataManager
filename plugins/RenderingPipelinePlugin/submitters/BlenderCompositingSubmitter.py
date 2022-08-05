from typing import List
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import SubmitterPipelineKeyRequirementsResponse
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os

class BlenderCompositingSubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        script = documentWithSettings.get(PipelineKeys.BlenderCompositingScript)
        pipelineInfoDict = documentWithSettings

        pluginName = deadline_nodes.getBlenderPipelinePluginName()
        jobName = self.pipeline.namingConvention.getPostName(documentWithSettings)
        batchName = 'Blender Compositing'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio + 1, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineBlenderCompositingPool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getPostFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, ext in enumerate(RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)):
            filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            jobInfoDict[f'OutputDirectory{i}'] = os.path.dirname(filename)
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        frames = documentWithSettings.get(PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, documentWithSettings.get(PipelineKeys.Perspective, '')), '')
        pipelineInfoDict[PipelineKeys.Frames] = frames

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineBlenderCompositingTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineBlenderCompositingInfo)

        extraPluginInfoDict = {
            "BaseScene": self.pipeline.namingConvention.getBlenderCompositingSceneFilename(documentWithSettings) if documentWithSettings.get(PipelineKeys.BlenderCompositingSceneNaming) else ''
        }

        return deadline_nodes.submitBlenderPipelineJob(script, pipelineInfoDict, jobInfoDict, 
                                                       blenderVersion=documentWithSettings.get(PipelineKeys.BlenderVersion), extraPluginInfoDict=extraPluginInfoDict)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.BlenderCompositingScript, 
                                                        messages=['A blender compositing script is not specified.'])