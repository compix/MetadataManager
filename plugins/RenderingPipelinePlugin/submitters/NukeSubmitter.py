from typing import List
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import SubmitterPipelineKeyRequirementsResponse
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os

class NukeSubmitter(RenderingPipelineSubmitter):
    defaultActive = True

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        if documentWithSettings.get(PipelineKeys.Mapping):
            return

        pluginName = deadline_nodes.getNukePluginName()
        jobName = self.pipeline.namingConvention.getPostName(documentWithSettings)
        batchName = 'Nuke'
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, self.baseDeadlinePriority + 1, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineNukePool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getPostFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, ext in enumerate(RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)):
            filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            jobInfoDict[f'OutputDirectory{i}'] = os.path.dirname(filename)
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineNukeTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineNukeInfo)

        sceneFilename = self.pipeline.namingConvention.getNukeSceneFilename(documentWithSettings)
        scriptFilename = documentWithSettings.get(PipelineKeys.NukeScript)

        pluginInfoDict = deadline_nodes.createNukePluginInfoDictionary(sceneFilename, version=documentWithSettings.get(PipelineKeys.NukeVersion))
        scriptInfoDict = documentWithSettings

        return deadline_nodes.submitNukeJob(jobInfoDict, pluginInfoDict, scriptFilename, scriptInfoDict, jobDependencies=dependentJobIds)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.NukeScript, 
                                                        messages=['A nuke script is not specified.'], isFile=True)