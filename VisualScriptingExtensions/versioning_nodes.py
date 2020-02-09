from VisualScripting.node_exec.base_nodes import defNode
from MetadataManagerCore.versioning import file_versioning

IDENTIFIER = "Versioning"

@defNode("Get Version Folder", isExecutable=True, returnNames=["Version Folder"], identifier=IDENTIFIER)
def getVersionFolder(baseVersioningFolder, versionNumber=None):
    return file_versioning.getVersionFolder(baseVersioningFolder, versionNumber)

@defNode("Create File Version", isExecutable=True, returnNames=["New Version Number"], identifier=IDENTIFIER)
def createFileVersion(srcFilePath, destFolder, maxVersionCount):
    return file_versioning.createFileVersion(srcFilePath, destFolder, maxVersionCount)