from MetadataManagerCore.filtering.DocumentFilter import DocumentFilter
from MetadataManagerCore import Keys

class DocumentTagsFilter(DocumentFilter):
    def __init__(self, active = False) -> None:
        super().__init__(filterFunction=self.filterFunc, uniqueFilterLabel='Has Tags', active=active, hasStringArg=True)

        self.tags = []

    def preApply(self):
        if self.args:
            self.tags = [t.strip() for t in self.args.split(',')]

    def filterFunc(self, document: dict, args: str):
        tags =  document.get(Keys.TAGS)
        return tags and all(tag in tags for tag in self.tags)
