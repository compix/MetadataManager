from os import pipe
from plugins.RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.actions.Action import Action
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from typing import List
import os
import typing
from RenderingPipelinePlugin.PipelineType import PipelineType

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

    def execute(self, document: dict, submitInputSceneCreation: bool, submitRenderSceneCreation: bool, submitRendering: bool, submitNuke: bool, submitCopyForDelivery: bool):
        lastJobId = None

        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        submitter = self.pipeline.submitter

        if submitInputSceneCreation:
            lastJobId = submitter.submitInputSceneCreation(documentWithSettings, dependentJobIds=lastJobId)
        
        if submitRenderSceneCreation:
            lastJobId = submitter.submitRenderSceneCreation(documentWithSettings, dependentJobIds=lastJobId)

        if submitRendering:
            lastJobId = submitter.submitRendering(documentWithSettings, dependentJobIds=lastJobId)

        if submitNuke:
            lastJobId = submitter.submitNuke(documentWithSettings, dependentJobIds=lastJobId)

        if submitCopyForDelivery:
            submitter.submitCopyForDelivery(documentWithSettings, dependentJobIds=lastJobId)

class CollectionUpdateAction(PipelineAction):
    @property
    def runsOnMainThread(self):
        return True
        
    @property
    def displayName(self):
        return 'Update Collection'

    def execute(self, productTablePath: str, productTableSheetName: str):
        self.pipeline.readProductTable(productTablePath, productTableSheetName, self.pipeline.environmentSettings, onProgressUpdate=self.updateProgress)
        self.pipeline.environment.settings[PipelineKeys.ProductTable] = productTablePath.replace('\\', '/')
        self.pipeline.environment.settings[PipelineKeys.ProductTableSheetName] = productTableSheetName
        self.pipeline.environmentManager.saveToDatabase()

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
        windows_nodes.selectInExplorer(filename)

class SelectPostImageInExplorerAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Select Post Image in Explorer'

    def execute(self, document):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        filename = self.pipeline.namingConvention.getPostFilename(documentWithSettings, ext=self.pipeline.getPreferredPreviewExtension(documentWithSettings))
        windows_nodes.selectInExplorer(filename)