from typing import List
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore import Keys
from MetadataManagerCore.mongodb_manager import MongoDBManager
import logging

logger = logging.getLogger(__name__)

class DocumentTaggingAction(DocumentAction):
    def __init__(self, dbManager: MongoDBManager):
        super().__init__()

        self.dbManager = dbManager

    @property
    def id(self):
        return 'Tag'
        
    def execute(self, document: dict, tags: List[str], replaceExistingTags: bool):
        # Get the current tags of the document
        if replaceExistingTags:
            document[Keys.TAGS] = tags
        else:
            currentTags = document.get(Keys.TAGS)

            if currentTags:
                for newTag in tags:
                    if not newTag in currentTags:
                        currentTags.append(newTag)
            else:
                currentTags = tags

            document[Keys.TAGS] = currentTags


        collectionName = document.get(Keys.collection)
        sid = document.get(Keys.systemIDKey)
        if collectionName:
            self.dbManager.insertOrModifyDocument(collectionName, sid, document, True)
        else:
            logger.warning(f'The document {sid} does not have a collection key {Keys.collection}')

