from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os
from MetadataManagerCore import Keys

def replaceGermanCharacters(input: str):
    return input.replace('ö', 'oe').replace('ü', 'ue').replace('ä', 'ae').replace('Ä', 'AE').replace('Ü', 'UE').replace('Ö', 'OE').replace('ß', 'ss').replace('ẞ', 'SS')

def extractNameFromNamingConvention(namingConvention: str, documentWithSettings: dict):
    if not namingConvention:
        # Apply default convention by using the sid
        return documentWithSettings.get(Keys.systemIDKey, '')

    keyExtractionInProgress = False
    curKey = ''
    name = ''
    for c in namingConvention:
        if c == '[':
            keyExtractionInProgress = True
        elif c == ']':
            keyExtractionInProgress = False
            value = documentWithSettings.get(curKey, '')
            if value == None:
                value = ''
            name += value
            curKey = ''
        elif keyExtractionInProgress:
            curKey += c
        else:
            name += c
    
    if documentWithSettings.get(PipelineKeys.ReplaceGermanCharacters, ''):
        name = replaceGermanCharacters(name)

    return name

class NamingConvention(object):
    def __init__(self) -> None:
        super().__init__()

    def addFilenameInfo(self, documentWithSettings: dict):
        """Adds filenames to the given documentWithSettings dictionary. Note that post and delivery filenames are without extensions because multiple output extensions are possible.

        Args:
            documentWithSettings (dict): The dictionary of the document merged with environment settings.
        """
        documentWithSettings[PipelineKeys.BaseSceneFilename] = self.getBaseSceneFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.InputSceneFilename] = self.getInputSceneFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.RenderSceneFilename] = self.getRenderSceneFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.EnvironmentSceneFilename] = self.getEnvironmentSceneFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.NukeSceneFilename] = self.getNukeSceneFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.RenderingFilename] = self.getRenderingFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.PostFilename] = self.getPostFilename(documentWithSettings)
        documentWithSettings[PipelineKeys.DeliveryFilename] = self.getDeliveryFilename(documentWithSettings)

    # Names without extension

    def getRenderSceneName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.BaseSceneNaming, ''), documentWithSettings))
        
    def getRenderSceneName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.RenderSceneNaming, ''), documentWithSettings))

    def getInputSceneName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.InputSceneNaming, ''), documentWithSettings))

    def getEnvironmentSceneName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.EnvironmentSceneNaming, ''), documentWithSettings))

    def getNukeSceneName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.NukeSceneNaming, ''), documentWithSettings))

    def getPerspectiveDependentNaming(self, documentWithSettings: dict, namingKey: str):
        key = PipelineKeys.getKeyWithPerspective(namingKey, documentWithSettings.get(PipelineKeys.Perspective, ''))
        renderingName = documentWithSettings.get(key, '')
        if not renderingName:
            renderingName = documentWithSettings.get(namingKey, '')

        return renderingName

    def getRenderingName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.RenderingNaming), documentWithSettings))

    def getPostName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.PostNaming), documentWithSettings))

    def getDeliveryName(self, documentWithSettings: dict):
        return os.path.basename(extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.DeliveryNaming), documentWithSettings))

    # Relative filenames without extension

    def getBaseSceneRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.BaseSceneNaming, ''), documentWithSettings)

    def getRenderSceneRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.RenderSceneNaming, ''), documentWithSettings)

    def getInputSceneRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.InputSceneNaming, ''), documentWithSettings)

    def getEnvironmentSceneRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.EnvironmentSceneNaming, ''), documentWithSettings)

    def getNukeSceneRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.NukeSceneNaming, ''), documentWithSettings)

    def getRenderingRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.RenderingNaming), documentWithSettings)

    def getPostRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.PostNaming), documentWithSettings)

    def getDeliveryRelPath(self, documentWithSettings: dict):
        return extractNameFromNamingConvention(self.getPerspectiveDependentNaming(documentWithSettings, PipelineKeys.DeliveryNaming), documentWithSettings)

    # Absolute filenames with extension

    def getInputSceneFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.InputScenesFolder, ''), self.getInputSceneRelPath(documentWithSettings)) + f'.{documentWithSettings.get(PipelineKeys.SceneExtension, "")}'

    def getRenderSceneFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.RenderScenesFolder, ''), self.getRenderSceneRelPath(documentWithSettings)) + f'.{documentWithSettings.get(PipelineKeys.SceneExtension, "")}'

    def getEnvironmentSceneFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.EnvironmentScenesFolder, ''), self.getEnvironmentSceneRelPath(documentWithSettings)) + f'.{documentWithSettings.get(PipelineKeys.SceneExtension, "")}'

    def getNukeSceneFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.NukeScenesFolder, ''), self.getNukeSceneRelPath(documentWithSettings)) + f'.nk'

    def getRenderingFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.RenderingsFolder, ''), self.getRenderingRelPath(documentWithSettings)) + f'.{documentWithSettings.get(PipelineKeys.RenderingExtension, "")}'

    def getPostFilename(self, documentWithSettings: dict, ext: str = None):
        return os.path.join(documentWithSettings.get(PipelineKeys.PostFolder, ''), self.getPostRelPath(documentWithSettings)) + (f'.{ext}' if ext else '')

    def getDeliveryFilename(self, documentWithSettings: dict, ext: str = None):
        return os.path.join(documentWithSettings.get(PipelineKeys.DeliveryFolder, ''), self.getDeliveryRelPath(documentWithSettings)) + (f'.{ext}' if ext else '')

    def getBaseSceneFilename(self, documentWithSettings: dict):
        return os.path.join(documentWithSettings.get(PipelineKeys.BaseScenesFolder, ''), self.getBaseSceneRelPath(documentWithSettings)) + f'.{documentWithSettings.get(PipelineKeys.SceneExtension, "")}'