from typing import List
from MetadataManagerCore.task_processor.DataRetrievalType import DataRetrievalType
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.NamingConvention import extractNameFromNamingConvention
from RenderingPipelinePlugin.submitters.MetadataManagerSubmissionTaskSettings import MetadataManagerSubmissionTaskSettings
from RenderingPipelinePlugin.submitters.RenderingPipelineSubmitter import RenderingPipelineSubmitter
import VisualScriptingExtensions.third_party_extensions.deadline_nodes as deadline_nodes
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os

class MetadataManagerTaskSubmitter(RenderingPipelineSubmitter):
    def __init__(self, pipeline, metadataManagerTaskSettings: MetadataManagerSubmissionTaskSettings) -> None:
        super().__init__(pipeline)

        self.metadataManagerTaskSettings = metadataManagerTaskSettings

    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pluginName = deadline_nodes.getMetadataManagerPluginName()
        jobName = self.pipeline.namingConvention.getDeliveryName(documentWithSettings)
        batchName = self.metadataManagerTaskSettings.name
        basePrio = self.getBaseDeadlinePriority(documentWithSettings)
        jobInfoDict = self.createJobInfoDictionary(pluginName, jobName, batchName, basePrio, 
                                                   documentWithSettings.get(PipelineKeys.DeadlineDeliveryPool), dependentJobIds=dependentJobIds)

        # Make sure the output folder exists:
        outputDir = os.path.dirname(self.pipeline.namingConvention.getDeliveryFilename(documentWithSettings))
        os.makedirs(outputDir, exist_ok=True)

        for i, filename in enumerate(self.metadataManagerTaskSettings.outputFilenamesDict.values()):
            filename = extractNameFromNamingConvention(filename, documentWithSettings)
            outputDir = os.path.dirname(filename)
            os.makedirs(outputDir, exist_ok=True)

            jobInfoDict[f'OutputDirectory{i}'] = outputDir
            jobInfoDict[f'OutputFilename{i}'] = os.path.basename(filename)

        # TODO: Provide user input per custom task
        self.setTimeout(jobInfoDict, documentWithSettings, PipelineKeys.DeadlineDeliveryTimeout)

        actionId = self.metadataManagerTaskSettings.actionId
        taskType = self.metadataManagerTaskSettings.taskType or 'RenderingPipelineDocumentAction'

        taskInfoDict = deadline_nodes.createMetadataManagerActionTaskDictForDocument(taskType=taskType, actionId=actionId, document=documentWithSettings, 
            collections=[self.pipeline.dbCollectionName], dataRetrievalType=DataRetrievalType.UseSubmittedData.value, submittedData=documentWithSettings)

        return deadline_nodes.submitMetadataManagerJob(taskInfoDict, jobInfoDict, jobDependencies=dependentJobIds)