import typing
from RenderingPipelinePlugin import PipelineKeys
from RenderingPipelinePlugin.PipelineType import PipelineType
from RenderingPipelinePlugin.submitters import submitter_mapping
from RenderingPipelinePlugin.submitters.MetadataManagerSubmissionTaskSettings import MetadataManagerSubmissionTaskSettings
from RenderingPipelinePlugin.submitters.BlenderCompositingSubmitter import BlenderCompositingSubmitter
from RenderingPipelinePlugin.submitters.DeliveryCopySubmitter import DeliveryCopySubmitter
from RenderingPipelinePlugin.submitters.Max3dsSubmitter import Max3dsInputSceneCreationSubmitter, Max3dsRenderSceneCreationSubmitter, Max3dsRenderingSubmitter
from RenderingPipelinePlugin.submitters.MetadataManagerTaskSubmitter import MetadataManagerTaskSubmitter
from RenderingPipelinePlugin.submitters.UnrealEngineSubmitter import UnrealEngineInputSceneCreationSubmitter, UnrealEngineRenderSceneCreationSubmitter, UnrealEngineRenderingSubmitter
from RenderingPipelinePlugin.submitters.BlenderSubmitter import BlenderInputSceneCreationSubmitter, BlenderRenderSceneCreationSubmitter, BlenderRenderingSubmitter
from RenderingPipelinePlugin.submitters.NukeSubmitter import NukeSubmitter

class SubmitterInfo(object):
    def __init__(self, name: str, submitterClass) -> None:
        super().__init__()

        self.name = name
        self.submitterClass = submitterClass
        self.taskView = None
        self.taskSettings: MetadataManagerSubmissionTaskSettings = None

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SubmitterInfo) and self.name == other.name and self.taskView == other.taskView

    def toDict(self):
        return {
            'name': self.name,
            'className': self.submitterClass.__name__
        }

    @staticmethod
    def fromDict(d: dict):
        submitterClass = submitter_mapping.ClassNameToClassMap.get(d.get('className'))
        return SubmitterInfo(d.get('name'), submitterClass)

def getOrderedSubmitterInfos(envSettings: dict) -> typing.List[SubmitterInfo]:
    submitterInfoDicts = envSettings.get(PipelineKeys.OrderedSubmitterInfos)
    submitterInfos = []

    mdTaskSubmitterDicts = envSettings.get(PipelineKeys.CustomTasks)
    nameToTaskSettings: typing.Dict[str, MetadataManagerSubmissionTaskSettings] = dict()
    if mdTaskSubmitterDicts:
        for taskDict in mdTaskSubmitterDicts:
            taskSettings = MetadataManagerSubmissionTaskSettings(taskDict)
            nameToTaskSettings[taskSettings.name] = taskSettings

    if submitterInfoDicts:
        for infoDict in submitterInfoDicts:
            submitterInfo = SubmitterInfo.fromDict(infoDict)
            taskSettings = nameToTaskSettings.get(submitterInfo.name)
            submitterInfo.taskSettings = taskSettings
            submitterInfos.append(submitterInfo)

    pipelineType = envSettings.get(PipelineKeys.PipelineType)
    if not pipelineType is None:
        pipelineType = PipelineType(pipelineType)
        for i in getPipelineSubmitterInfos(pipelineType):
            if not i in submitterInfos:
                submitterInfos.append(i)
        
    for i in getPostSubmitterInfos():
        if not i in submitterInfos:
            submitterInfos.append(i)

    for taskSettings in nameToTaskSettings.values():
        info = SubmitterInfo(taskSettings.name, MetadataManagerTaskSubmitter)
        info.taskSettings = taskSettings
        if not info in submitterInfos:
            submitterInfos.append(info)

    return submitterInfos

def getSubmitterName(submitterClass) -> str:
    name = submitterClass.__name__
    t_name = ''
    for i, c in enumerate(name):
        if i > 0 and c.isupper():
            t_name += ' '

        t_name += c

    return t_name
    
def getPipelineSubmitterInfos(pipelineType: PipelineType) -> typing.List[SubmitterInfo]:
    pipelineSubmitterClasses = []
    if pipelineType == PipelineType.Max3ds:
        pipelineSubmitterClasses = [Max3dsInputSceneCreationSubmitter, Max3dsRenderSceneCreationSubmitter, Max3dsRenderingSubmitter]
    elif pipelineType == PipelineType.Blender:
        pipelineSubmitterClasses = [BlenderInputSceneCreationSubmitter, BlenderRenderSceneCreationSubmitter, BlenderRenderingSubmitter]
    elif pipelineType == PipelineType.UnrealEngine:
        pipelineSubmitterClasses = [UnrealEngineInputSceneCreationSubmitter, UnrealEngineRenderSceneCreationSubmitter, UnrealEngineRenderingSubmitter]

    return [SubmitterInfo(getSubmitterName(_class), _class) for _class in pipelineSubmitterClasses]

def getPostSubmitterInfos() -> typing.List[SubmitterInfo]:
    return [SubmitterInfo(getSubmitterName(_class), _class) for _class in [NukeSubmitter, BlenderCompositingSubmitter, DeliveryCopySubmitter]]