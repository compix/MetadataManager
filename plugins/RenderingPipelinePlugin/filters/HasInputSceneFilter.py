from RenderingPipelinePlugin.filters.PipelineFilter import PipelineFilter
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class HasInputSceneFilter(PipelineFilter):
    def __init__(self, pipeline: 'RenderingPipeline' = None, active = False) -> None:
        super().__init__(pipeline, filterFunction=self.filterFunc, uniqueFilterLabel='Has Input Scene', active=active, hasStringArg=False)

        self.pipeline = pipeline

    def filterFunc(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        inputSceneFilename = self.pipeline.namingConvention.getInputSceneFilename(documentWithSettings)
        
        return inputSceneFilename and os.path.exists(inputSceneFilename)