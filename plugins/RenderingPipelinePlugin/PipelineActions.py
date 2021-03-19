from os import pipe
from plugins.RenderingPipelinePlugin import PipelineKeys
from MetadataManagerCore.actions.Action import Action
from MetadataManagerCore.actions.DocumentAction import DocumentAction
from typing import List
import os
import typing
from RenderingPipelinePlugin.PipelineType import PipelineType

if typing.TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline

class PipelineDocumentAction(DocumentAction):
    def __init__(self, pipeline: 'RenderingPipeline'):
        super().__init__()

        self.pipeline = pipeline

    @property
    def id(self):
        return f'{self.pipeline.name}_{self.__class__.__name__}'

class CopyForDeliveryDocumentAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return "Copy for Delivery"

    def execute(self, document: dict):
        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        self.pipeline.copyForDelivery(documentWithSettings)

class SubmissionAction(PipelineDocumentAction):
    @property
    def displayName(self):
        return 'Submit'

    def execute(self, document: dict, submitInputSceneCreation: bool, submitRenderSceneCreation: bool, submitRendering: bool, submitNuke: bool, submitCopyForDelivery: bool):
        # TODO: Pass action actions via retrieveActionArgs in Viewer
        lastJobId = None

        documentWithSettings = self.pipeline.combineDocumentWithSettings(document, self.pipeline.environmentSettings)
        submitter = self.pipeline.submitter

        if submitInputSceneCreation:
            lastJobId = submitter.submitInputSceneCreation(documentWithSettings, dependentJobIds=lastJobId)
        
        if submitRenderSceneCreation:
            lastJobId = submitter.submitRenderSceneCreation(documentWithSettings, dependentJobIds=lastJobId)

        if submitRendering:
            lastJobId = submitter.submitRendering(documentWithSettings, dependentJobIds=lastJobId)

        if submitNuke:
            lastJobId = submitter.submitNuke(documentWithSettings, dependentJobIds=lastJobId)

        if submitCopyForDelivery:
            submitter.submitCopyForDelivery(documentWithSettings, dependentJobIds=lastJobId)
    