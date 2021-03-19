from RenderingPipelinePlugin.submitters.Submitter import Submitter
from RenderingPipelinePlugin.submitters.BlenderSubmitter import BlenderSubmitter
from RenderingPipelinePlugin.submitters.Max3dsSubmitter import Max3dsSubmitter
import asset_manager
from typing import Dict, List
from table import table_util
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.environment.Environment import Environment
from MetadataManagerCore.mongodb_manager import MongoDBManager
from RenderingPipelinePlugin.NamingConvention import NamingConvention
from RenderingPipelinePlugin.NamingConvention import extractNameFromNamingConvention
import hashlib
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os
from MetadataManagerCore import Keys
import shutil
import logging
from RenderingPipelinePlugin.PipelineType import PipelineType

logger = logging.getLogger(__name__)

class RenderingPipeline(object):
    def __init__(self, name: str, environmentManager: EnvironmentManager, dbManager: MongoDBManager) -> None:
        super().__init__()
        
        self.name = name
        self.environmentManager = environmentManager
        self.dbManager = dbManager

        self._namingConvention = NamingConvention()

    def setNamingConvention(self, namingConvention: NamingConvention):
        self._namingConvention = namingConvention

    @property
    def namingConvention(self):
        if self._namingConvention:
            return self._namingConvention

        if self.environmentSettings:
            return NamingConvention(self.environmentSettings)

        return None

    @property
    def environmentSettings(self) -> dict:
        return self.environmentManager.getEnvironmentFromName(self.environmentName).getEvaluatedSettings()

    @property
    def pipelineType(self) -> PipelineType:
        return PipelineType(self.environmentSettings[PipelineKeys.PipelineType])

    @namingConvention.setter
    def namingConvention(self, nc: NamingConvention):
        self._namingConvention = nc

    @property
    def dbCollectionName(self) -> str:
        return self.name.replace(' ', '')

    @property
    def environmentName(self) -> str:
        return self.name

    @property
    def environment(self) -> Environment:
        return self.environmentManager.getEnvironmentFromName(self.environmentName)

    @property
    def environmentSettings(self) -> dict:
        environment = self.environmentManager.getEnvironmentFromName(self.environmentName)
        if environment:
            return environment.getEvaluatedSettings()
        
        return None

    def combineDocumentWithSettings(self, document: dict, settings: dict):
        docCopy = document.copy()
        for key, value in settings.items():
            if not key in document:
                docCopy[key] = value

        return docCopy

    def getPreferredPreviewExtension(self, settings: dict):
        postOutputExtensions = RenderingPipelineUtil.getPostOutputExtensions(settings)
        postOutputExt = postOutputExtensions[0]
        for ext in ['jpg', 'png', 'tif']:
            if ext in postOutputExtensions:
                postOutputExt = ext
                break

        return postOutputExt

    def getSID(self, documentWithSettings: dict, tableRow: List[str]):
        sid = extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.SidNaming), documentWithSettings)
        if not sid:
            # Concat all entries into one string:
            rowStr = ''.join(tableRow)
            sid = hashlib.md5(rowStr.encode('utf-8')).hexdigest()

        return sid

    def copyForDelivery(self, documentWithSettings: dict):
        outputExtensions = RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)

        for ext in outputExtensions:
            postFilename = self.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            deliveryFilename= self.namingConvention.getDeliveryFilename(documentWithSettings, ext=ext)

            if os.path.exists(postFilename):
                os.makedirs(os.path.dirname(deliveryFilename), exist_ok=True)
                shutil.copy2(postFilename, deliveryFilename)

    @property
    def submitter(self) -> Submitter:
        if self.pipeline.pipelineType == PipelineType.Max3ds:
            return Max3dsSubmitter(self)
        elif self.pipeline.pipelineType == PipelineType.Blender:
            return BlenderSubmitter(self)

        return None
        
    def readProductTable(self, productTablePath: str = None, productTableSheetname: str = None, environmentSettings: dict = None):
        table = table_util.readTable(productTablePath, excelSheetName=productTableSheetname)

        if not table:
            raise RuntimeError(f'Could not read table {productTablePath}' + (f' with sheet name {productTableSheetname}.' if productTableSheetname else '.'))

        header = table.getHeader()

        # In case of rendering name duplicates, create mappings/links to the document with the first-assigned rendering.
        renderingToDocumentMap: Dict[str,dict] = dict()

        sidSet = set()
        rowIdx = 0

        for row in table.getRowsWithoutHeader():
            # Convert values to string for consistency
            row = [str(v) for v in row]
            documentDict = table.getRowAsDict(header, row)
            
            if PipelineKeys.Perspective in documentDict:
                perspectiveCodes = [documentDict[PipelineKeys.Perspective]]
            else:
                perspectiveCodes = RenderingPipelineUtil.getPerspectiveCodes(environmentSettings)

                if len(perspectiveCodes) == 0:
                    perspectiveCodes.append('')

            postOutputExt = self.getPreferredPreviewExtension(environmentSettings)

            for perspectiveCode in perspectiveCodes:
                documentDict[PipelineKeys.Perspective] = perspectiveCode

                documentWithSettings = self.combineDocumentWithSettings(documentDict, environmentSettings)

                sid = self.getSID(documentWithSettings, row)

                if sid in sidSet:
                    logger.warning(f'Duplicate sid {sid} found at row {rowIdx}. This row will be skipped.')
                    continue
                else:
                    sidSet.add(sid)

                    renderingName = extractNameFromNamingConvention(PipelineKeys.RenderingNaming, documentWithSettings)
                    mappedDocument = renderingToDocumentMap.get(renderingName)

                    if mappedDocument:
                        documentWithSettings[PipelineKeys.Mapping] = mappedDocument.get(Keys.systemIDKey)

                    documentWithSettings[Keys.systemIDKey] = sid
                    documentWithSettings[Keys.preview] = self.namingConvention.getPostFilename(documentWithSettings, postOutputExt)

                    self.dbManager.insertOrModifyDocument(self.dbCollectionName, sid, documentDict, checkForModifications=False)

            rowIdx += 1