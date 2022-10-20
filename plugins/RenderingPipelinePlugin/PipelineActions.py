from RenderingPipelinePlugin.submitters.Submitter import Submitter
from qt_extensions import qt_util
from MetadataManagerCore import Keys
from os import pipe
from plugins.RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.actions.Action import Action
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from typing import List
import os
import typing
from RenderingPipelinePlugin.PipelineType import PipelineType
from MetadataManagerCore.animation import anim_util

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

if os.name == 'nt':
    import VisualScripting.node_exec.windows_nodes as windows_nodes

class PipelineAction(Action):
    def __init__(self, pipeline: 'RenderingPipeline'):
        super().__init__()

        self.pipeline = pipeline

    @property
    def category(self):
        return "Rendering Pipeline"

    @property
    def id(self):
        return f'{self.pipeline.name}_{self.__class__.__name__}'

class PipelineDocumentAction(DocumentAction):
    def __init__(self, pipeline: 'RenderingPipeline'):
        super().__init__()

        self.pipeline = pipeline

    @property
    def category(self):
        return "Rendering Pipeline"

    @property
    def id(self):
        return f'{self.pipeline.name}_{self.__class__.__name__}'

class CopyForDeliveryDocumentAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return "Copy for Delivery"

    def execute(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        self.pipeline.copyForDelivery(documentWithSettings)

class SubmissionAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Submit'

    def execute(self, document: dict, basePriority: int, submitters: List[Submitter], initialStatus: str, resX: int, resY: int):
        lastJobId = None

        if resX != None and resY != None:
            document[PipelineKeys.ResolutionOverwriteX] = resX
            document[PipelineKeys.ResolutionOverwriteY] = resY
            
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        self.pipeline.namingConvention.addFilenameInfo(documentWithSettings)
        
        if basePriority != None:
            documentWithSettings[PipelineKeys.DeadlinePriority] = basePriority

        for submitter in submitters:
            if submitter.active:
                submitter.initialStatus = initialStatus
                lastJobId = submitter.submit(documentWithSettings, dependentJobIds=lastJobId)

    @property
    def runsOnMainThread(self):
        return False

class CollectionUpdateAction(PipelineAction):
    @property
    def runsOnMainThread(self):
        return True
        
    @property
    def displayName(self):
        return 'Update Collection'

    def execute(self, productTablePath: str, productTableSheetName: str):
        self.pipeline.readProductTable(productTablePath, productTableSheetName, self.pipeline.environmentSettings, onProgressUpdate=self.updateProgress)
        pipelineEnv = self.pipeline.environment
        pipelineEnv.settings[PipelineKeys.ProductTable] = productTablePath.replace('\\', '/')
        pipelineEnv.settings[PipelineKeys.ProductTableSheetName] = productTableSheetName
        self.pipeline.environmentManager.upsert(pipelineEnv.uniqueEnvironmentId)

        if self.pipeline.viewerRegistry.documentSearchFilterViewer:
            self.pipeline.viewerRegistry.documentSearchFilterViewer.viewItemsOverThreadPool(saveSearchHistoryEntry=False)

class SelectInputSceneInExplorerAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Select Input Scene in Explorer'

    def execute(self, document):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        filename = self.pipeline.namingConvention.getInputSceneFilename(documentWithSettings)
        windows_nodes.selectInExplorer(filename)

class SelectRenderSceneInExplorerAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Select Render Scene in Explorer'

    def execute(self, document):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        filename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        windows_nodes.selectInExplorer(filename)

class SelectRenderingInExplorerAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Select Rendering in Explorer'

    def execute(self, document):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        filename = self.pipeline.namingConvention.getRenderingFilename(documentWithSettings)

        if '#' in filename:
            frames = anim_util.extractExistingFrameFilenames(filename)

            if len(frames) > 0:
                filename = frames[0]
            else:
                return
        elif self.pipeline.pipelineType == PipelineType.Blender:
            base, ext = os.path.splitext(filename)
            filename = base + "0000" + ext

        windows_nodes.selectInExplorer(filename)

class SelectPostImageInExplorerAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Select Post Image in Explorer'

    def execute(self, document):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=self.pipeline.getPreferredPreviewExtension(documentWithSettings))
        if '#' in filename:
            frames = anim_util.extractExistingFrameFilenames(filename)
            if len(frames) > 0:
                windows_nodes.selectInExplorer(frames[0])        
        else:
            windows_nodes.selectInExplorer(filename)

class RefreshPreviewFilenameAction(PipelineAction):
    @property
    def displayName(self):
        return 'Refresh Preview Filenames'

    @property
    def runsOnMainThread(self):
        return True

    def execute(self):
        ext = self.pipeline.getPreferredPreviewExtension(self.pipeline.environmentSettings)
        collection = self.pipeline.dbManager.db[self.pipeline.dbCollectionName]

        for document in collection.find({}):
            documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
            filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            document[Keys.preview] = filename

            collection.replace_one({'_id': document['_id']}, document)
        
        qt_util.runInMainThread(lambda: self.pipeline.viewerRegistry.documentSearchFilterViewer.viewItems(saveSearchHistoryEntry=False))