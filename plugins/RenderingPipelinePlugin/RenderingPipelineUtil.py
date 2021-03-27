from typing import List
from RenderingPipelinePlugin import PipelineKeys

KnownPostOutputExtensions = ['jpg', 'jpeg', 'exr', 'tif', 'png', 'bmp', 'webp', 'gif']

def getPerspectiveCodes(settings: dict):
    return  [p.strip() for p in settings.get(PipelineKeys.PerspectiveCodes, '').split(',')]

def getPostOutputExtensions(settings: dict):
    return extractPostOutputExtensionsFromString(settings.get(PipelineKeys.PostOutputExtensions))

def extractPostOutputExtensionsFromString(extensionsStr: str) -> List[str]:
    return [ext.strip().lower() for ext in extensionsStr.split(',')]

def validatePostOutputExtensions(extensions: List[str]):
    return len(extensions) > 0 and all(ext in KnownPostOutputExtensions for ext in extensions)