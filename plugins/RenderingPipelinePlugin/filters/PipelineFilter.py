from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
import os

import typing

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class PipelineFilter(DocumentFilter):
    """Base class for pipeline filters.
    """
    def __init__(self, pipeline: 'RenderingPipeline' = None, filterFunction = None, uniqueFilterLabel : str = None, active : bool = False, hasStringArg : bool = False) -> None:
        super().__init__(filterFunction=filterFunction, uniqueFilterLabel=uniqueFilterLabel, active=active, hasStringArg=hasStringArg)

        self.pipeline = pipeline

    def copy(self):
        f = self.__class__(self.pipeline)
        f.filterFunction = self.filterFunction
        f.setFromDict(self.asDict())
        return f