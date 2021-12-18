import typing
from MetadataManagerCore import Keys
from NodeGraphQt.constants import NODE_PROP_QCOMBO
from VisualScripting.node_exec.base_nodes import BaseCustomNode, ComboBoxInput, InlineNode, defNode
from RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.animation import anim_util
from VisualScriptingExtensions.document_action_nodes import DocumentActionNode
from dist.MetadataManager.plugins.RenderingPipelinePlugin import RenderingPipelineUtil
from dist.MetadataManager.plugins.RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from dist.MetadataManager.plugins.RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager

IDENTIFIER = 'Rendering Pipeline'

RENDERING_PIPELINE_MANAGER: RenderingPipelineManager = None

def refreshPipelineComboBox(node: BaseCustomNode):
    curSelection = node.get_property('pipelineComboMenu')
    node.comboBoxNodeWidget.clear()

    if RENDERING_PIPELINE_MANAGER != None:
        pipelineNames = RENDERING_PIPELINE_MANAGER.pipelineNames
        node.comboBoxNodeWidget.add_items(pipelineNames)

        node.deleteProperty("pipelineComboMenu")
        node.create_property("pipelineComboMenu", pipelineNames[0] if len(pipelineNames) > 0 else None, items=pipelineNames, widget_type=NODE_PROP_QCOMBO)

        if curSelection != None:
            idx = pipelineNames.index(curSelection)
            if idx >= 0:
                node.comboBoxNodeWidget.widget.setCurrentIndex(idx)

class RenderingPipelineSelectionNode(InlineNode):
    __identifier__ = IDENTIFIER
    NODE_NAME = 'Select Rendering Pipeline'

    def __init__(self):
        super(RenderingPipelineSelectionNode,self).__init__()

        self.comboBoxNodeWidget = self.add_combo_menu("pipelineComboMenu", "Pipeline")
        self.add_output('Name')

        self.add_button("Refresh", self.onRefresh)
        self.onRefresh()

    def onRefresh(self):
        refreshPipelineComboBox(self)

    def getInlineCode(self):
        return '{!r}'.format(self.get_property('pipelineComboMenu'))

class RenderingPipelineDocumentActionNode(DocumentActionNode):
    __identifier__ = IDENTIFIER
    NODE_NAME = 'Rendering Pipeline Document Action'

    def execute(document: dict):
        pipeline: RenderingPipeline = RENDERING_PIPELINE_MANAGER.getPipelineFromCollectionName(document.get(Keys.collection))
        if not pipeline:
            return None

        documentWithSettings = pipeline.combineDocumentWithSettings(document, pipeline.environmentSettings)
        pipeline.namingConvention.addFilenameInfo(documentWithSettings)
        return documentWithSettings

def getAvailablePipelineKeysAsComboBoxItems():
    items = []
    for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
        value = getattr(PipelineKeys, key)
        items.append((key, value))

    return items

@defNode('Get Rendering Pipeline By Name', isExecutable=True, returnNames=['Pipeline'], identifier=IDENTIFIER)
def getRenderingPipelineByName(name: str) -> RenderingPipeline:
    return RENDERING_PIPELINE_MANAGER.getPipelineFromName(name)

@defNode('Get Existing Frame Filenames', isExecutable=True, returnNames=['Filenames'], identifier=IDENTIFIER)
def getExistingFrameFilenames(filenameWithHashtags: str) -> typing.List[str]:
    return anim_util.extractExistingFrameFilenames(filenameWithHashtags)

@defNode('Get Rendering Pipeline Document', isExecutable=True, returnNames=['Document'], identifier=IDENTIFIER)
def getRenderingPipelineDocument(document: dict=None) -> dict:
    if not document:
        return None

    pipeline: RenderingPipeline = RENDERING_PIPELINE_MANAGER.getPipelineFromCollectionName(document.get(Keys.collection))
    if not pipeline:
        return None

    documentWithSettings = pipeline.combineDocumentWithSettings(document, pipeline.environmentSettings)
    pipeline.namingConvention.addFilenameInfo(documentWithSettings)
    return documentWithSettings

@defNode('Get Rendering Pipeline Document Value', returnNames=['Value'], inputInfo={'key': ComboBoxInput(getAvailablePipelineKeysAsComboBoxItems())})
def getRenderingPipelineDocumentValue(renderingPipelineDocument: dict, key: str=''):
    if not renderingPipelineDocument:
        return None

    return renderingPipelineDocument.get(key)

@defNode('Rendering Pipeline Get All Post Output Extensions', returnNames=['Extensions'])
def renderingPipelineGetAllPostOutputFilenames(renderingPipelineDocument: dict=None):
    if not renderingPipelineDocument:
        return None

    return RenderingPipelineUtil.extractPostOutputExtensionsFromString(renderingPipelineDocument.get(PipelineKeys.PostOutputExtensions))

@defNode('Rendering Pipeline Get All Post Output Filenames', returnNames=['Filenames'])
def renderingPipelineGetAllPostOutputFilenames(renderingPipelineDocument: dict=None):
    if not renderingPipelineDocument:
        return None

    filenames = []
    fn = renderingPipelineDocument.get(PipelineKeys.PostFilename)
    extensions = RenderingPipelineUtil.extractPostOutputExtensionsFromString(renderingPipelineDocument.get(PipelineKeys.PostOutputExtensions))
    for ext in extensions:
        filename = f'{fn}.{ext}'
        if '#' in filename:
            filenames += anim_util.extractExistingFrameFilenames(filename)
        else:
            filenames.append(filename)

    return filenames

@defNode('Rendering Pipeline Get Post Output Filenames', returnNames=['Filenames'])
def renderingPipelineGetPostOutputFilenames(renderingPipelineDocument: dict=None, filenameExtension: str='jpg'):
    if not renderingPipelineDocument:
        return None

    filenames = []
    fn = renderingPipelineDocument.get(PipelineKeys.PostFilename)
    filename = f'{fn}.{filenameExtension}'
    if '#' in filename:
        filenames += anim_util.extractExistingFrameFilenames(filename)
    else:
        filenames.append(filename)

    return filenames

@defNode('Rendering Pipeline Get Post Output Filename', returnNames=['Filename'])
def renderingPipelineGetPostOutputFilename(renderingPipelineDocument: dict=None, filenameExtension: str='jpg', frame:int=None):
    if not renderingPipelineDocument:
        return None

    fn = renderingPipelineDocument.get(PipelineKeys.PostFilename)
    filename = f'{fn}.{filenameExtension}'
    if '#' in filename:
        filenames = anim_util.extractExistingFrameFilenames(filename)
        if frame is None:
            frame = 0
        
        if frame >= 0 and frame < len(filenames):
            return filenames[frame]
    else:
        return filename
    
    return None