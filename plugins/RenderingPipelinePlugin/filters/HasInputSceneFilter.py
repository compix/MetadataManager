from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class HasInputSceneFilter(DocumentFilter):
    def __init__(self, active = False) -> None:
        super().__init__(filterFunction=self.filterFunc, uniqueFilterLabel='Has Input Scene', active=active, hasStringArg=False)

        self.pipeline = None

    def setPipeline(self, pipeline: 'RenderingPipeline'):
        self.pipeline = pipeline

    def filterFunc(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        inputSceneFilename = self.pipeline.namingConvention.getInputSceneFilename(documentWithSettings)
        
        return inputSceneFilename and os.path.exists(inputSceneFilename)