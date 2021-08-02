from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class HasRenderSceneFilter(DocumentFilter):
    def __init__(self, pipeline: 'RenderingPipeline' = None, active = False) -> None:
        super().__init__(filterFunction=self.filterFunc, uniqueFilterLabel='Has Render Scene', active=active, hasStringArg=False)

        self.pipeline = pipeline

    def filterFunc(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        renderSceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        
        return renderSceneFilename and os.path.exists(renderSceneFilename)