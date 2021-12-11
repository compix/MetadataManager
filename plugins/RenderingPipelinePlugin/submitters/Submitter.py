from typing import List
import typing
from RenderingPipelinePlugin import PipelineKeys

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.submitters.SubmitterInfo import SubmitterInfo

class SubmitterRequirementsResponse(object):
    def __init__(self, satisfied=True, messages: List[str]=None) -> None:
        super().__init__()

        self.satisfied = satisfied
        self.messages = messages or []

class SubmitterPipelineKeyRequirementsResponse(object):
    def __init__(self, envSettings: dict, envKey: str, perspectiveDependent: bool = False, messages: List[str]=None) -> None:
        super().__init__()

        if perspectiveDependent:
            value = PipelineKeys.getKeyWithPerspective(envKey, envSettings.get(PipelineKeys.Perspective, ''))
            if not value:
                value = envSettings.get(envKey, '')    
        else:
            value = envSettings.get(envKey, '')
            
        self.satisfied = value.strip() != ''
        self.messages = messages

class Submitter(object):
    defaultActive = False

    def __init__(self) -> None:
        super().__init__()

        self.info: 'SubmitterInfo' = None
        self.active = False

    @property
    def name(self):
        name = self.__class__.__name__
        t_name = ''
        for c in name:
            t_name += c
            if c.isupper():
                t_name += ' '
        
        return t_name
        
    def submit(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass
    
    @staticmethod
    def checkRequirements(envSettings: dict) -> SubmitterRequirementsResponse:
        return SubmitterRequirementsResponse()