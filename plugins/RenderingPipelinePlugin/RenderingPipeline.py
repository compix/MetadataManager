import typing
from RenderingPipelinePlugin.filters.HasInputSceneFilter import HasInputSceneFilter
from RenderingPipelinePlugin.filters.HasRenderSceneFilter import HasRenderSceneFilter
from RenderingPipelinePlugin.filters.HasRenderingFilter import HasRenderingFilter
from RenderingPipelinePlugin.submitters.BlenderCompositingSubmitter import BlenderCompositingSubmitter
from RenderingPipelinePlugin.submitters.DeliveryCopySubmitter import DeliveryCopySubmitter
from RenderingPipelinePlugin.submitters.MetadataManagerSubmissionTaskSettings import MetadataManagerSubmissionTaskSettings
from RenderingPipelinePlugin.submitters.MetadataManagerTaskSubmitter import MetadataManagerTaskSubmitter
from RenderingPipelinePlugin.submitters.NukeSubmitter import NukeSubmitter
from RenderingPipelinePlugin.submitters.SubmitterInfo import SubmitterInfo, getOrderedSubmitterInfos
from RenderingPipelinePlugin.submitters.UnrealEngineSubmitter import UnrealEngineInputSceneCreationSubmitter, UnrealEngineRenderSceneCreationSubmitter, UnrealEngineRenderingSubmitter
from table.Table import Table
from viewers.ViewerRegistry import ViewerRegistry
from qt_extensions import qt_util
from MetadataManagerCore.Event import Event
from PySide2.QtWidgets import QCheckBox, QVBoxLayout
from ApplicationMode import ApplicationMode
from AppInfo import AppInfo
from ServiceRegistry import ServiceRegistry
from RenderingPipelinePlugin.submitters.Submitter import Submitter, SubmitterRequirementsResponse
from RenderingPipelinePlugin.submitters.BlenderSubmitter import BlenderInputSceneCreationSubmitter, BlenderRenderSceneCreationSubmitter, BlenderRenderingSubmitter
from RenderingPipelinePlugin.submitters.Max3dsSubmitter import Max3dsInputSceneCreationSubmitter, Max3dsRenderSceneCreationSubmitter, Max3dsRenderingSubmitter
import asset_manager
from typing import Callable, Dict, List
from table import table_util
from MetadataManagerCore.environment.Environment import Environment
from RenderingPipelinePlugin.NamingConvention import NamingConvention
from RenderingPipelinePlugin.NamingConvention import extractNameFromNamingConvention
import hashlib
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
import os
from MetadataManagerCore import Keys
import shutil
import logging
from RenderingPipelinePlugin.PipelineType import PipelineType
from RenderingPipelinePlugin.PipelineActions import RefreshPreviewFilenameAction, SelectInputSceneInExplorerAction, \
    SelectPostImageInExplorerAction, SelectRenderSceneInExplorerAction, \
    SelectRenderingInExplorerAction, SubmissionAction, CopyForDeliveryDocumentAction, CollectionUpdateAction
from MetadataManagerCore.actions.Action import Action
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
import uuid

logger = logging.getLogger(__name__)

class RenderingPipeline(object):
    def __init__(self, name: str, serviceRegistry: ServiceRegistry, viewerRegistry: ViewerRegistry, appInfo: AppInfo) -> None:
        super().__init__()
        
        self.name = name
        self.serviceRegistry = serviceRegistry
        self.viewerRegistry = viewerRegistry
        self.appInfo = appInfo
        self.environmentManager = serviceRegistry.environmentManager
        self.dbManager = serviceRegistry.dbManager
        self.submissionArgs = []
        self.collectionUpdateArgs = []

        self._namingConvention = NamingConvention()
        self.rowSkipConditions: Callable[[dict],bool] = []
        self.customData = None
        self.activated = False

        self.submissionCheckBoxStates: typing.Dict[str, bool] = dict()

    def activate(self):
        if not self.activated:
            self.registerAndLinkActions()
            self.addFilters()

            self.activated = True

    def setCustomDataEntry(self, key: str, value):
        if self.customData == None:
            self.customData = dict()

        self.customData[key] = value

    def getCustomDataValue(self, key: str, default = None):
        return self.customData.get(key) if self.customData else default

    def registerAndLinkActions(self):
        if self.appInfo.mode == ApplicationMode.GUI:
            self.setupAndRegisterSubmissionAction()
            self.setupAndRegisterCollectionUpdateAction()

        self.registerAndLinkAction(CopyForDeliveryDocumentAction(self))
        self.registerAndLinkAction(SelectInputSceneInExplorerAction(self))
        self.registerAndLinkAction(SelectRenderSceneInExplorerAction(self))
        self.registerAndLinkAction(SelectRenderingInExplorerAction(self))
        self.registerAndLinkAction(SelectPostImageInExplorerAction(self))
        self.registerAndLinkAction(RefreshPreviewFilenameAction(self))

    def addFilters(self):
        self.serviceRegistry.documentFilterManager.addFilter(HasInputSceneFilter(self), self.dbCollectionName)
        self.serviceRegistry.documentFilterManager.addFilter(HasRenderSceneFilter(self), self.dbCollectionName)
        self.serviceRegistry.documentFilterManager.addFilter(HasRenderingFilter(self), self.dbCollectionName)

    def registerAndLinkAction(self, action: Action):
        self.serviceRegistry.actionManager.registerAction(action)
        self.serviceRegistry.actionManager.linkActionToCollection(action.id, self.dbCollectionName)

    @property
    def submitCheckboxLayout(self) -> QVBoxLayout:
        return self.submissionDialog.submitCheckboxLayout

    def onSubmit(self):
        submitters = self.submitters
        for i in range(self.submitCheckboxLayout.count()):
            item = self.submitCheckboxLayout.itemAt(i)
            checkbox: QCheckBox = item.widget()
            submitter = submitters[i]
            submitter.active = checkbox.isChecked()
            if submitter.info:
                self.submissionCheckBoxStates[submitter.info.name] = checkbox.isChecked()

        priority = int(self.submissionDialog.basePriorityEdit.text()) if self.submissionDialog.basePriorityEdit.text() else None
        initialStatus = self.submissionDialog.initialStatusComboBox.currentText()

        self.submissionArgs = [priority, submitters, initialStatus]
        self.submissionDialog.accept()

    def setupAndRegisterSubmissionAction(self):
        submissionAction = SubmissionAction(self)
        self.registerAndLinkAction(submissionAction)

        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "assets/submissionDialog.ui")
        self.submissionDialog = asset_manager.loadDialogAbsolutePath(uiFilePath)

        self.submissionDialog.basePriorityEdit.setValidator(RegexPatternInputValidator('^\d*$'))
        self.submissionDialog.cancelButton.clicked.connect(self.submissionDialog.reject)
        self.submissionDialog.submitButton.clicked.connect(self.onSubmit)

        submissionAction.confirmationEvent = Event()
        self.submissionDialog.accepted.connect(lambda: submissionAction.confirmationEvent())
        submissionAction.requestConfirmationFunction = self.onOpenSubmissionDialog
        submissionAction.retrieveArgsFunction = lambda: self.submissionArgs

    def onOpenSubmissionDialog(self):
        def addCheckBox(submitterInfo: SubmitterInfo):
            layout: QVBoxLayout = self.submissionDialog.submitCheckboxLayout
            checkBox = QCheckBox(submitterInfo.name.rstrip('Submitter'))

            response: SubmitterRequirementsResponse = submitterInfo.submitterClass.checkRequirements(self.environmentSettings)
            
            if response.satisfied:
                checkBox.setEnabled(True)
                checkBox.setToolTip("")
                lastState = self.submissionCheckBoxStates.get(submitterInfo.name)
                if not lastState is None:
                    checkBox.setChecked(lastState)
                else:
                    checkBox.setChecked(submitterInfo.submitterClass.defaultActive)
            else:
                checkBox.setEnabled(False)
                checkBox.setChecked(False)
                checkBox.setToolTip(", ".join(response.messages))

            layout.addWidget(checkBox)

        qt_util.clearContainer(self.submissionDialog.submitCheckboxLayout)

        submitterInfos = getOrderedSubmitterInfos(self.environmentSettings)
        for submitterInfo in submitterInfos:
            addCheckBox(submitterInfo, )

        self.submissionDialog.basePriorityEdit.setText(str(self.environmentSettings.get(PipelineKeys.DeadlinePriority, '')))
        self.submissionDialog.open()

    def onDialogUpdateCollection(self):
        if not os.path.exists(self.updateCollectionDialog.tablePathEdit.text()):
            self.updateCollectionDialog.statusLabel.setText('The selected file does not exist.')
            return

        self.collectionUpdateArgs = [self.updateCollectionDialog.tablePathEdit.text(), self.updateCollectionDialog.sheetNameComboBox.currentText().strip()]
        self.updateCollectionDialog.accept()

    def onUpdateCollectionTablePathEditTextChanged(self, txt: str):
        self.updateCollectionDialog.sheetNameComboBox.clear()

        if os.path.exists(txt):
            sheetNames = table_util.getSheetNames(txt)
            if sheetNames:
                for sheetName in sheetNames:
                    self.updateCollectionDialog.sheetNameComboBox.addItem(sheetName)

    def setupAndRegisterCollectionUpdateAction(self):
        action = CollectionUpdateAction(self)
        self.registerAndLinkAction(action)

        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "assets/updateCollectionDialog.ui")
        self.updateCollectionDialog = asset_manager.loadDialogAbsolutePath(uiFilePath)
        self.updateCollectionDialog.statusLabel.setText('')

        self.updateCollectionDialog.cancelButton.clicked.connect(self.updateCollectionDialog.reject)
        self.updateCollectionDialog.updateButton.clicked.connect(self.onDialogUpdateCollection)

        qt_util.connectFileSelection(self.updateCollectionDialog, self.updateCollectionDialog.tablePathEdit, self.updateCollectionDialog.tablePathButton)
        self.updateCollectionDialog.tablePathEdit.textChanged.connect(self.onUpdateCollectionTablePathEditTextChanged)

        action.confirmationEvent = Event()
        self.updateCollectionDialog.accepted.connect(lambda: action.confirmationEvent())
        action.requestConfirmationFunction = self.updateCollectionDialog.open
        action.retrieveArgsFunction = lambda: self.collectionUpdateArgs

        env = self.environment
        if env:
            settings = env.getEvaluatedSettings()
            tablePath = settings.get(PipelineKeys.ProductTable)
            sheetName = settings.get(PipelineKeys.ProductTableSheetName)

            if tablePath:
                self.updateCollectionDialog.tablePathEdit.setText(tablePath)
                if sheetName:
                    self.updateCollectionDialog.sheetNameComboBox.setCurrentText(sheetName)

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
        for ext in ['png', 'jpg', 'tif']:
            if ext in postOutputExtensions:
                postOutputExt = ext
                break

        return postOutputExt

    def getSID(self, documentWithSettings: dict, tableRow: List[str]):
        sid = extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.SidNaming), documentWithSettings)
        if not sid:
            # Concat all entries into one string:
            rowStr = ''.join([v for v in tableRow if v]) + documentWithSettings.get(PipelineKeys.Perspective, "")
            sid = hashlib.md5(rowStr.encode('utf-8')).hexdigest()

        sid += f'_{self.dbCollectionName}'
        return sid

    def copyForDelivery(self, documentWithSettings: dict):
        outputExtensions = RenderingPipelineUtil.getPostOutputExtensions(documentWithSettings)

        for ext in outputExtensions:
            postFilename = self.namingConvention.getPostFilename(documentWithSettings, ext=ext)
            deliveryFilename= self.namingConvention.getDeliveryFilename(documentWithSettings, ext=ext)

            if os.path.exists(postFilename):
                os.makedirs(os.path.dirname(deliveryFilename), exist_ok=True)
                shutil.copy2(postFilename, deliveryFilename)
            else:
                logger.warning(f'The source file {postFilename} does not exist.')

    @property
    def submitters(self) -> List[Submitter]:
        submitterInfos = getOrderedSubmitterInfos(self.environmentSettings)

        submitters = []
        for submitterInfo in submitterInfos:
            if submitterInfo.taskSettings:
                submitter = MetadataManagerTaskSubmitter(self, submitterInfo.taskSettings)
            else:
                submitter = submitterInfo.submitterClass(self)
            
            submitter.info = submitterInfo
            submitters.append(submitter)

        return submitters

    def setRowSkipConditions(self, rowSkipConditions: Callable[[dict],bool]):
        self.rowSkipConditions = rowSkipConditions

    def processHeader(self, header: List[str], rowIndices: List[str]):
        pass

    def processDocumentDict(self, documentDict: dict, logHandler: Callable[[str],None] = None):
        return True

    def postProcessDocumentDict(self, documentDict: dict, logHandler: Callable[[str],None] = None):
        return True

    def zipRowAndHeader(self, row: List[str], header: List[str], rowIndices: List[str]):
        return {header[hi]: row[i] for hi, i in enumerate(rowIndices) if i < len(row)}

    def processRows(self, table: Table, collectionName: str, header: typing.List[str], rowIndices: typing.List[int], environmentSettings: dict = None,
                    onProgressUpdate: Callable[[float, str],None] = None, logHandler: Callable[[str],None] = None):

        # In case of rendering name duplicates, create mappings/links to the document with the first-assigned rendering.
        renderingToDocumentMap: Dict[str,dict] = dict()

        sidSet = set()
        rowIdx = 1
        rowCount = table.nrows

        for row in table.getRowsWithoutHeader():
            # Convert values to string for consistency
            row = [str(v) if v != None else v for v in row]
            documentDict = self.zipRowAndHeader(row, header, rowIndices)

            if any(rowSkipCondition(documentDict) for rowSkipCondition in self.rowSkipConditions):
                continue

            if not self.processDocumentDict(documentDict, logHandler):
                continue
            
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
                documentDict[Keys.systemIDKey] = sid
                documentWithSettings[Keys.systemIDKey] = sid

                if not self.postProcessDocumentDict(documentDict, logHandler):
                    continue

                if sid in sidSet:
                    m = f'Duplicate sid {sid} found at row {rowIdx}. This row will be skipped.'
                    logger.warning(m)
                    if logHandler:
                        logHandler(m)
                    continue
                else:
                    sidSet.add(sid)

                    renderingName = extractNameFromNamingConvention(documentWithSettings.get(PipelineKeys.RenderingNaming), documentWithSettings)
                    mappedDocument = renderingToDocumentMap.get(renderingName)

                    documentDict[Keys.preview] = self.namingConvention.getPostFilename(documentWithSettings, postOutputExt)

                    if mappedDocument:
                        documentDict[PipelineKeys.Mapping] = mappedDocument.get(Keys.systemIDKey)
                    else:
                        renderingToDocumentMap[renderingName] = documentDict
                        documentDict[PipelineKeys.Mapping] = None

                    self.dbManager.insertOrModifyDocument(collectionName, sid, documentDict, checkForModifications=False)

            rowIdx += 1

            if onProgressUpdate:
                onProgressUpdate(float(rowIdx) / rowCount)

    def readProductTable(self, productTablePath: str = None, productTableSheetname: str = None, environmentSettings: dict = None, 
                         onProgressUpdate: Callable[[float, str],None] = None, replaceExistingCollection=False, logHandler: Callable[[str],None] = None):
        """Generates a database collection with rendering entries from the given table.

        Args:
            productTablePath (str, optional): [description]. Defaults to None.
            productTableSheetname (str, optional): [description]. Defaults to None.
            environmentSettings (dict, optional): [description]. Defaults to None.
            onProgressUpdate (Callable[[float, str],None], optional): [description]. The first argument is the progress in [0,1], the second is the progress message (optional). Defaults to None.

        Raises:
            RuntimeError: [description]
        """
        table = table_util.readTable(productTablePath, excelSheetName=productTableSheetname)

        if not table:
            raise RuntimeError(f'Could not read table {productTablePath}' + (f' with sheet name {productTableSheetname}.' if productTableSheetname else '.'))

        header = []
        rowIndices = []
        for i,h in enumerate(table.getHeader()):
            if h:
                header.append(h)
                rowIndices.append(i)

        self.processHeader(header, rowIndices)

        if onProgressUpdate:
            onProgressUpdate(0, 'Reading product table...')

        collectionName = self.dbCollectionName

        droppedTempCollection = False

        if replaceExistingCollection:
            tempCollectionName = f'{self.dbCollectionName}_{uuid.uuid4().hex[:6]}'
            try:
                existingCollection = self.dbManager.db[collectionName]
                if existingCollection.count() > 0:
                    self.dbManager.db[collectionName].rename(tempCollectionName)
                else:
                    replaceExistingCollection = False
            except Exception as e:
                raise RuntimeError(f'Failed to rename collection {collectionName} to temporary collection {tempCollectionName}. Maybe it already exists?')

        try:
            self.processRows(table, collectionName, header, rowIndices, environmentSettings, onProgressUpdate, logHandler)

            if replaceExistingCollection:
                self.dbManager.dropCollection(self.dbCollectionName + Keys.OLD_VERSIONS_COLLECTION_SUFFIX)
                self.dbManager.dropCollection(tempCollectionName)
                droppedTempCollection = True

            self.dbManager.addMissingHeaderInfos(self.dbCollectionName, header)
        except Exception as e:
            logger.error(str(e))
            if logHandler:
                logHandler(str(e))

            # Undo
            if replaceExistingCollection and not droppedTempCollection:
                self.dbManager.dropCollection(collectionName)
                self.dbManager.db[tempCollectionName].rename(collectionName)

            raise e