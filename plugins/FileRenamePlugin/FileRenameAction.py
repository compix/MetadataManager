from MetadataManagerCore.actions.Action import Action
from MetadataManagerCore.animation import anim_util
from typing import List
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from MetadataManagerCore import Keys
from MetadataManagerCore.mongodb_manager import MongoDBManager
import os
import re
import shutil
import logging

logger = logging.getLogger(__name__)

class FileRenameAction(Action):
    @property
    def id(self):
        return 'Rename Files'
        
    def execute(self, sourceFolder: str, sourceBasenameRegexPattern: str, targetFolder: str, targetFilenamePattern: str, targetFolders: str, recurse: bool, copy: bool):
        try:
            for root, dirs, files in os.walk(sourceFolder):
                if targetFolders:
                    for dirName in dirs:
                        dirfilename = os.path.join(root, dirName)
                        if targetFolder and os.path.normpath(dirfilename) == os.path.normpath(targetFolder):
                            continue

                        if not re.search(sourceBasenameRegexPattern, dirfilename):
                            continue

                        targetBasename = re.sub(sourceBasenameRegexPattern, targetFilenamePattern, dirName)
                        if targetFolder:
                            targetFilename = os.path.join(targetFolder, targetBasename)
                        else:
                            targetFilename = os.path.join(root, targetBasename)

                        if copy:
                            shutil.copytree(dirfilename, targetFilename)
                        else:
                            os.rename(dirfilename, targetFilename)

                else:
                    for fn in files:
                        filename = os.path.join(root, fn)
                        if targetFolder and os.path.normpath(os.path.dirname(filename)) == os.path.normpath(targetFolder):
                            continue

                        if not re.search(sourceBasenameRegexPattern, filename):
                            continue

                        targetBasename = re.sub(sourceBasenameRegexPattern, targetFilenamePattern, fn)
                        if targetFolder:
                            targetFilename = os.path.join(targetFolder, targetBasename)
                        else:
                            targetFilename = os.path.join(root, targetBasename)

                        if copy:
                            shutil.copy2(filename, targetFilename)
                        else:
                            os.rename(filename, targetFilename)

                if not recurse:
                    break
                    
        except Exception as e:
            logger.error(f'Failed with exception: {str(e)}')

