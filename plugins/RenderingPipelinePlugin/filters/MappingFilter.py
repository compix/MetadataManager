from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
from RenderingPipelinePlugin import PipelineKeys

class MappingFilter(DocumentFilter):
    def __init__(self, active = False) -> None:
        super().__init__(filterFunction=self.filterFunc, uniqueFilterLabel='Is Mapping', active=active, hasStringArg=False)

    def filterFunc(self, document: dict):
        return document.get(PipelineKeys.Mapping)