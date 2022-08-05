from typing import List
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
from RenderingPipelinePlugin.submitters.Submitter import SubmitterPipelineKeyRequirementsResponse
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os

class DeliveryCopySubmitter(RenderingPipelineSubmitter):
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pluginName = deadline_nodes.getMetadataManagerPluginName()
        jobName = self.pipeline.namingConvention.getDeliveryName(documentWithSettings)
        batchName = 'Delivery Copy'
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineDeliveryPool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, ext in enumerate(RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)):
            filename = self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings, ext=ext)
            jobInfoDict[f'OutputDirectory{i}'] = os.path.dirname(filename)
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineDeliveryTimeout)
        self.setNodesBlackWhitelist(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineDeliveryInfo)

        actionId = f'{self.pipeline.name}_CopyForDeliveryDocumentAction'

        taskInfoDict = deadline_nodes.createMetadataManagerActionTaskDictForDocument(actionId=actionId, document=documentWithSettings, collections=[self.pipeline.dbCollectionName])

        return deadline_nodes.submitMetadataManagerJob(taskInfoDict, jobInfoDict, jobDependencies=dependentJobIds)

    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterPipelineKeyRequirementsResponse:
        return SubmitterPipelineKeyRequirementsResponse(envSettings, PipelineKeys.DeliveryNaming, perspectiveDependent=True, 
                                                        messages=['Delivery naming convention not specified.'])