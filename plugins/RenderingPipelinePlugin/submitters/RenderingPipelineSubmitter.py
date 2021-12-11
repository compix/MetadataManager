from RenderingPipelinePlugin.NamingConvention import replaceGermanCharacters
from RenderingPipelinePlugin import PipelineKeys
from typing import List
import typing
import logging
from RenderingPipelinePlugin.submitters.Submitter import Submitter
logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class RenderingPipelineSubmitter(Submitter):
    def __init__(self, pipeline: 'RenderingPipeline') -> None:
        super().__init__()

        self.pipeline = pipeline
        self.initialStatus = 'Active'

    @property
    def baseDeadlinePriority(self):
        priority = self.pipeline.environmentSettings.get(PipelineKeys.DeadlinePriority)
        if priority != None:
            return int(priority)

        return 50

    def setTimeout(self, jobInfoDict: dict, documentWithSettings: dict, timeoutKey: str):
        timeout = documentWithSettings.get(timeoutKey)
        if timeout != None and timeout.strip() != '' and timeout != 'None':
            try:
                jobInfoDict['TaskTimeoutMinutes'] = int(timeout)
            except Exception as e:
                logger.error(str(e))

    def createJobInfoDictionary(self, pluginName: str, name: str, batchName: str, priority: int, pool: str, dependentJobIds: List[str]=None):
        d = {"Plugin": pluginName, 
             "Name": replaceGermanCharacters(name),
             "BatchName": replaceGermanCharacters(f'{self.pipeline.name} {batchName}'), 
             "Priority": priority, 
             "Department":"", 
             "Pool":pool, 
             "SecondaryPool":"",
             "Group":"",
             "InitialStatus": self.initialStatus if not dependentJobIds else 'Active'}

        if dependentJobIds:
            d["JobDependencies"] = (",".join(dependentJobIds) if isinstance(dependentJobIds, list) else dependentJobIds)

        return d