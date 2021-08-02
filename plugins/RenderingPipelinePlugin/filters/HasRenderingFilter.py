from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
from MetadataManagerCore.animation import anim_util
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class HasRenderingFilter(DocumentFilter):
    def __init__(self, pipeline: 'RenderingPipeline' = None, active = False) -> None:
        super().__init__(filterFunction=self.filterFunc, uniqueFilterLabel='Has Rendering', active=active, hasStringArg=False)

        self.pipeline = pipeline

    def filterFunc(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        renderingFilename = self.pipeline.namingConvention.getRenderingFilename(documentWithSettings)
        
        return renderingFilename and anim_util.hasExistingFrameFilenames(renderingFilename)