import typing
from VisualScripting.node_exec.base_nodes import ComboBoxInput, defNode
from RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.animation import anim_util

IDENTIFIER = 'Rendering Pipeline'

def getAvailablePipelineKeysAsComboBoxItems():
    items = []
    for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
        value = getattr(PipelineKeys, key)
        items.append((key, value))

    return items

@defNode('Get Existing Frame Filenames', isExecutable=True, returnNames=['Filenames'], identifier=IDENTIFIER)
def getExistingFrameFilenames(filenameWithHashtags: str) -> typing.List[str]:
    return anim_util.extractExistingFrameFilenames(filenameWithHashtags)

@defNode('Get Rendering Pipeline Env Value', returnNames=['Value'], inputInfo={'key': ComboBoxInput(getAvailablePipelineKeysAsComboBoxItems())})
def getRenderingPipelineEnvValue(environmentSettings: dict=None, key: str=''):
    if not environmentSettings:
        environmentSettings = dict()

    return environmentSettings.get(key)