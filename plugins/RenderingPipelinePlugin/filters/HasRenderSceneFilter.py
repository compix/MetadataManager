from RenderingPipelinePlugin.filters.PipelineFilter import PipelineFilter
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class HasRenderSceneFilter(PipelineFilter):
    def __init__(self, pipeline: 'RenderingPipeline' = None, active = False) -> None:
        super().__init__(pipeline, filterFunction=self.filterFunc, uniqueFilterLabel='Has Render Scene', active=active, hasStringArg=False)
        
    def filterFunc(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        renderSceneFilename = self.pipeline.namingConvention.getRenderSceneFilename(documentWithSettings)
        
        return renderSceneFilename and os.path.exists(renderSceneFilename)