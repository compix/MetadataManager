from animation import anim_util
from typing import List
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore import Keys
from MetadataManagerCore.mongodb_manager import MongoDBManager
import os
import re
import shutil
import logging

logger = logging.getLogger(__name__)

class DocumentFileCopyAction(DocumentAction):
    @property
    def id(self):
        return 'Copy Linked File'
        
    def execute(self, document: dict, documentFileKey: str, targetFolder: str, extendHashtagToAnimationFrame, rename: bool = False, sourceFilenameRegexPattern: str = None, targetFilenamePattern: str = None):
        srcFilename = document.get(documentFileKey)

        if not srcFilename:
            return
        
        try:
            if extendHashtagToAnimationFrame and '#' in srcFilename:
                srcFilenames = anim_util.extractExistingFrameFilenames(srcFilename)
            else:
                srcFilenames = [srcFilename]

            os.makedirs(targetFolder, exist_ok=True)

            for srcFilename in srcFilenames:
                if not os.path.exists(srcFilename):
                    logging.warning(f'The file {srcFilename} does not exist.')
                    continue

                srcBasename = os.path.basename(srcFilename)

                if rename:
                    srcBasenameWithoutExt, ext = os.path.splitext(srcBasename)

                    if re.search(sourceFilenameRegexPattern, srcBasenameWithoutExt):
                        targetBasename = re.sub(sourceFilenameRegexPattern, targetFilenamePattern, srcBasenameWithoutExt) + (ext if ext else '')
                    else:
                        logger.warning(f'Failed to match {sourceFilenameRegexPattern} with {srcBasenameWithoutExt}')
                        continue
                else:
                    targetBasename = srcBasename

                shutil.copy2(srcFilename, os.path.join(targetFolder, targetBasename))

        except Exception as e:
            logger.error(f'Failed with exception: {str(e)}')

