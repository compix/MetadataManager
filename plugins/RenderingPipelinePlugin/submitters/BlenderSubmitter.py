from RenderingPipelinePlugin.submitters.Submitter import Submitter
from typing import List

class BlenderSubmitter(Submitter):
    def submitInputSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitRenderSceneCreation(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitRendering(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass

    def submitNuke(self, documentWithSettings: dict, dependentJobIds: List[str]=None):
        pass