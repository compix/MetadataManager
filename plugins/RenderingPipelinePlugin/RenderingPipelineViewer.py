import PySide2
from table import table_util
from qt_extensions.InputConfirmDialog import InputConfirmDialog
from AppInfo import AppInfo
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from RenderingPipelinePlugin.filters.MappingFilter import MappingFilter
from ServiceRegistry import ServiceRegistry
from MetadataManagerCore import Keys
from typing import List

from RenderingPipelinePlugin.PipelineType import PipelineType
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager, RenderingPipelinesCollectionName
import asset_manager
from qt_extensions import qt_util
from qt_extensions.ProgressDialog import ProgressDialog
from PySide2 import QtGui, QtWidgets
from MetadataManagerCore.environment.Environment import Environment
import os
import xlrd
import logging
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
from VisualScriptingExtensions.third_party_extensions.deadline_nodes import getDeadlinePoolNames
from MetadataManagerCore.threading import threading_util
from viewers.ViewerRegistry import ViewerRegistry
from enum import Enum
import re

logger = logging.getLogger(__name__)

class MaxSourceTemplateSceneType:
    InputScene = 'InputScene'
    RenderScene = 'RenderScene'

class EnvironmentEntry(object):
    def __init__(self, envKey: str, widget: QtWidgets.QWidget, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None) -> None:
        super().__init__()

        self.envKey = envKey
        self.widget = widget
        self.pipelineType = pipelineType
        self.pipelineComboBox = pipelineComboBox

    def saveValue(self, environment: Environment):
        pass

    def loadValue(self, environment: Environment):
        pass

    def isApplicable(self):
        if self.pipelineType and self.pipelineComboBox:
            return self.pipelineType == PipelineType(self.pipelineComboBox.currentText())

        return True

class EnvironmentEntryLineEdit(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        environment.settings[self.envKey] = edit.text()

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(environment.settings.get(self.envKey))

class EnvironmentEntryComboBox(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        environment.settings[self.envKey] = cb.currentText()

    def loadValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        cb.setCurrentText(environment.settings.get(self.envKey))

class RenderingPipelineViewer(object):
    def __init__(self, parentWindow, renderingPipelineManager: RenderingPipelineManager, serviceRegistry: ServiceRegistry, viewerRegistry: ViewerRegistry, appInfo: AppInfo):
        super().__init__()

        Keys.hiddenCollections.add(RenderingPipelinesCollectionName)
        
        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "assets/renderingPipeline.ui")
        self.dialog = asset_manager.loadDialogAbsolutePath(uiFilePath, fixedSize=False)

        self.serviceRegistry = serviceRegistry
        self.viewerRegistry = viewerRegistry
        self.appInfo = appInfo
        self.environmentEntries: List[EnvironmentEntry] = []
        
        self.renderingPipelineManager = renderingPipelineManager
        self.environmentManager = self.renderingPipelineManager.environmentManager
        self.dbManager = self.renderingPipelineManager.dbManager
        self.pipelineSelectionMenu = None
        self.pipelineNameActions = []

        self.renderingPipelineManager.onPipelineClassRegistrationEvent.subscribe(lambda _: self.updatePipelineClassComboBox())

        self.updatePipelineClassComboBox()
        self.setupPipelineTypeComboBox()

        self.dialog.createButton.clicked.connect(self.onCreateClick)
        self.dialog.deleteButton.clicked.connect(self.onDeleteClick)
        self.dialog.cancelButton.clicked.connect(self.hide)

        self.dialog.deleteButton.setVisible(False)

        self.refreshPipelineNameComboBox()
        self.dialog.pipelineNameComboBox.currentTextChanged.connect(self.onPipelineNameChanged)
        self.dialog.productTableEdit.textChanged.connect(self.onProductTableChanged)
        self.dialog.productTableSheetNameComboBox.currentTextChanged.connect(self.onProductTableSheetNameChanged)
        self.dialog.copyToClipboardButton.clicked.connect(lambda: QtGui.QGuiApplication.clipboard().setText(self.dialog.nukeSourceCodeTemplateEdit.toPlainText()))

        self.dialog.statusLabel.setText('')
        self.dialog.statusLabel.setStyleSheet('color: red')

        self.dialog.pipelineNameComboBox.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_ ]*$'))
        self.dialog.perspectiveCodesEdit.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_ ,]*$'))
        self.dialog.sidNamingEdit.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_\]\[]*$'))

        self.currentHeader = []

        qt_util.connectFolderSelection(self.dialog, self.dialog.baseProjectFolderEdit, self.dialog.baseProjectFolderButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.renderSceneCreationScriptEdit, self.dialog.renderSceneCreationScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.inputSceneCreationScriptEdit, self.dialog.inputSceneCreationScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.nukeScriptEdit, self.dialog.nukeScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.productTableEdit, self.dialog.productTableButton, filter='Table File (*.xlsx;*.csv)')
        qt_util.connectFileSelection(self.dialog, self.dialog.baseSceneEdit, self.dialog.baseSceneButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.renderSettingsEdit, self.dialog.renderSettingsButton)

        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.renderScenesFolderEdit, self.dialog.renderScenesFolderButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.inputScenesFolderEdit, self.dialog.inputScenesFolderButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.environmentScenesEdit, self.dialog.environmentScenesButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.nukeScenesFolderEdit, self.dialog.nukeScenesFolderButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.renderingsFolderEdit, self.dialog.renderingsFolderButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.postFolderEdit, self.dialog.postFolderButton)
        self.connectRelativeProjectFolderSelection(self.dialog, self.dialog.deliveryFolderEdit, self.dialog.deliveryFolderButton)

        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlinePriority, self.dialog.deadlinePriorityEdit))
        self.environmentEntries.append(EnvironmentEntryComboBox(PipelineKeys.Max3dsVersion, self.dialog.versionOf3dsMaxComboBox, PipelineType.Max3ds, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(EnvironmentEntryComboBox(PipelineKeys.NukeVersion, self.dialog.nukeVersionComboBox))

        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlineInputSceneTimeout, self.dialog.inputSceneDeadlineTimeout))
        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlineRenderSceneTimeout, self.dialog.renderSceneDeadlineTimeout))
        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlineRenderingTimeout, self.dialog.renderingDeadlineTimeout))
        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlineNukeTimeout, self.dialog.nukeDeadlineTimeout))
        self.environmentEntries.append(EnvironmentEntryLineEdit(PipelineKeys.DeadlineDeliveryTimeout, self.dialog.deliveryDeadlineTimeout))

        threading_util.runInThread(self.fetchDeadlinePoolNames)

        self.projectSubfolderDict = self.renderingPipelineManager.loadProjectSubfolderDict()

        self.refreshAvailablePipelineMenu()
        self.initProjectSubfolders()
        self.updateTabs()
        self.registerFilters()

        self.viewerRegistry.collectionViewer.refreshCollections()

    def registerFilters(self):
        self.serviceRegistry.documentFilterManager.addFilter(MappingFilter())

    def refreshPipelineNameComboBox(self):
        currentText = self.dialog.pipelineNameComboBox.currentText()

        self.dialog.pipelineNameComboBox.clear()

        for pipelineName in self.renderingPipelineManager.pipelineNames:
            self.dialog.pipelineNameComboBox.addItem(pipelineName)

        self.dialog.pipelineNameComboBox.setCurrentText(currentText)

    def refreshAvailablePipelineMenu(self):
        menuBar = self.viewerRegistry.mainWindowManager.menuBar

        if not self.pipelineSelectionMenu:
            self.pipelineSelectionMenu = QtWidgets.QMenu("Select Rendering Pipeline")
            self.pipelineSelectionMenu.setObjectName('renderingPipelineSelectionMenu')
            menuBar.addMenu(self.pipelineSelectionMenu)

        self.pipelineNameActions.clear()
        self.pipelineSelectionMenu.clear()

        for pipelineName in self.renderingPipelineManager.pipelineNames:
            pipelineSelectionAction = QtWidgets.QAction(pipelineName)
            self.pipelineNameActions.append(pipelineSelectionAction)
            pipelineSelectionAction.triggered.connect((lambda selectedPipeline: lambda: self.onPipelineSelected(selectedPipeline))(pipelineName))
            self.pipelineSelectionMenu.addAction(pipelineSelectionAction)

        selectedPipelineName = self.appInfo.settings.value('SelectedRenderingPipeline')
        if selectedPipelineName:
            self.pipelineSelectionMenu.setTitle(f'Selected RP: {selectedPipelineName}')

    def onPipelineSelected(self, pipelineName: str):
        self.selectPipelineFromName(pipelineName)

    def selectPipelineFromName(self, pipelineName: str):
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        if pipeline:
            self.viewerRegistry.collectionViewer.showSingleCollection(pipeline.dbCollectionName)
            self.viewerRegistry.environmentManagerViewer.setCurrentEnvironment(pipeline.environment)
            self.viewerRegistry.documentSearchFilterViewer.viewItems(saveSearchHistoryEntry=False)
            self.pipelineSelectionMenu.setTitle(f'Selected RP: {pipeline.name}')
            self.appInfo.settings.setValue('SelectedRenderingPipeline', pipeline.name)

    def fetchDeadlinePoolNames(self):
        poolNames = getDeadlinePoolNames(quiet=True)
        qt_util.runInMainThread(self.onDeadlinePoolNamesFetched, poolNames)

    def onDeadlinePoolNamesFetched(self, poolNames: List[str]):
        self.setupDeadlinePoolComboBox(self.dialog.deadlineInputScenePoolComboBox, poolNames, PipelineKeys.DeadlineInputScenePool)
        self.setupDeadlinePoolComboBox(self.dialog.deadlineRenderScenePoolComboBox, poolNames, PipelineKeys.DeadlineRenderScenePool)
        self.setupDeadlinePoolComboBox(self.dialog.deadlineRenderingPoolComboBox, poolNames, PipelineKeys.DeadlineRenderingPool)
        self.setupDeadlinePoolComboBox(self.dialog.deadlineNukePoolComboBox, poolNames, PipelineKeys.DeadlineNukePool)
        self.setupDeadlinePoolComboBox(self.dialog.deadlineDeliveryPoolComboBox, poolNames, PipelineKeys.DeadlineDeliveryPool)

    def setupDeadlinePoolComboBox(self, comboBox: QtWidgets.QComboBox, poolNames: List[str], envKey: str):
        self.environmentEntries.append(EnvironmentEntryComboBox(envKey, comboBox))

        if poolNames:
            for poolName in poolNames:
                comboBox.addItem(poolName)

    def initProjectSubfolders(self):
        self.dialog.renderScenesFolderEdit.setText(self.projectSubfolderDict.get(PipelineKeys.RenderingsFolder, ''))
        self.dialog.inputScenesFolderEdit.setText(self.projectSubfolderDict.get(PipelineKeys.InputScenesFolder, ''))
        self.dialog.environmentScenesEdit.setText(self.projectSubfolderDict.get(PipelineKeys.EnvironmentScenesFolder, ''))
        self.dialog.renderingsFolderEdit.setText(self.projectSubfolderDict.get(PipelineKeys.RenderingsFolder, ''))
        self.dialog.postFolderEdit.setText(self.projectSubfolderDict.get(PipelineKeys.PostFolder, ''))
        self.dialog.deliveryFolderEdit.setText(self.projectSubfolderDict.get(PipelineKeys.DeliveryFolder, ''))

    def connectRelativeProjectFolderSelection(self, parentWidget, lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, initialDir=""):
        def onSelect():
            dirName = QtWidgets.QFileDialog.getExistingDirectory(parentWidget, "Open", initialDir)
            if dirName != None and dirName != "":
                baseProjectFolder = self.dialog.baseProjectFolderEdit.text()
                if os.path.normpath(dirName).startswith(os.path.normpath(baseProjectFolder)):
                    dirName = os.path.relpath(dirName, baseProjectFolder)

                lineEdit.setText(dirName)
        
        button.clicked.connect(onSelect)
    
    def onDeleteClick(self):
        # Confirm by user:
        pipelineName = self.dialog.pipelineNameComboBox.currentText()
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        if not pipeline:
            return

        def onConfirmPipelineDeletion():
            self.renderingPipelineManager.deletePipeline(pipelineName)
            self.refreshPipelineNameComboBox()
            self.dialog.pipelineNameComboBox.setCurrentText('')
            self.refreshAvailablePipelineMenu()
            self.viewerRegistry.collectionViewer.refreshCollections()
            self.viewerRegistry.environmentManagerViewer.refreshEnvironmentsComboBox()

        self.deleteInputConfirmDialog = InputConfirmDialog(pipelineName, onConfirmPipelineDeletion, title='Delete Confirmation', confirmButtonText='Delete')
        self.deleteInputConfirmDialog.open()

    def verifyNamingConvention(self, namingConvention: str, namingConventionName: str):
        namingRegexPattern = '^([\w\d]*(\[[\w\d]*\])*)*$'
        valid = re.search(namingRegexPattern, namingConvention) != None

        if not valid:
            self.dialog.statusLabel.setText(f'The naming convetion for {namingConventionName} is not valid.')

        return valid

    def onCreateClick(self):
        pipelineName = self.dialog.pipelineNameComboBox.currentText()

        envId = self.environmentManager.getIdFromEnvironmentName(pipelineName)

        if not self.dialog.headerConfirmationCheckBox.isChecked():
            self.dialog.statusLabel.setText(f'Please confirm the table extraction.')
            return

        notAllowedHeaderKeys = [Keys.preview]
        if any(key in self.currentHeader for key in notAllowedHeaderKeys):
            self.dialog.statusLabel.setText(f'The following table header keys are used internally by the pipeline and thus should not be present: {notAllowedHeaderKeys}')
            return

        baseProjectFolder = self.dialog.baseProjectFolderEdit.text()
        pipelineType = self.dialog.pipelineTypeComboBox.currentText()
        pipelineClassName = self.dialog.pipelineClassComboBox.currentText()
        renderSceneCreationScript = self.dialog.renderSceneCreationScriptEdit.text()
        inputSceneCreationScript = self.dialog.inputSceneCreationScriptEdit.text()
        nukeScript = self.dialog.nukeScriptEdit.text()
        productTable = self.dialog.productTableEdit.text()
        sheetName = self.dialog.productTableSheetNameComboBox.currentText()
        baseScene = self.dialog.baseSceneEdit.text()
        renderSettingsFile = self.dialog.renderSettingsEdit.text()
        replaceGermanChars = self.dialog.replaceGermanCharactersCheckBox.isChecked()
        perspectiveCodesStr = self.dialog.perspectiveCodesEdit.text()
        renderingExtension = self.dialog.renderingExtensionComboBox.currentText()
        postOutputExtensionsStr = self.dialog.postOutputExtensionsEdit.text()

        renderScenesFolder = self.dialog.renderScenesFolderEdit.text()
        inputScenesFolder = self.dialog.inputScenesFolderEdit.text()
        environmentScenesFolder = self.dialog.environmentScenesEdit.text()
        nukeScenesFolder = self.dialog.nukeScenesFolderEdit.text()
        renderingsFolder = self.dialog.renderingsFolderEdit.text()
        postFolder = self.dialog.postFolderEdit.text()
        deliveryFolder = self.dialog.deliveryFolderEdit.text()

        sidNaming = self.dialog.sidNamingEdit.text()
        renderSceneNaming = self.dialog.renderSceneNamingEdit.text()
        inputSceneNaming = self.dialog.inputSceneNamingEdit.text()
        environmentSceneNaming = self.dialog.environmentSceneNamingEdit.text()
        nukeSceneNaming = self.dialog.nukeSceneNamingEdit.text()
        renderingNaming = self.dialog.renderingNamingEdit.text()
        postNaming = self.dialog.postNamingEdit.text()
        deliveryNaming = self.dialog.deliveryNamingEdit.text()

        if not sidNaming:
            self.dialog.statusLabel.setText(f'SID naming convention must be specified.')
            return

        if not baseProjectFolder or not os.path.isabs(baseProjectFolder) or not os.path.exists(baseProjectFolder):
            self.dialog.statusLabel.setText(f'Please specify an existing base project folder.')
            return

        if not os.path.exists(productTable):
            self.dialog.statusLabel.setText(f'Please specify a valid product table path.')
            return

        if not RenderingPipelineUtil.validatePostOutputExtensions(RenderingPipelineUtil.extractPostOutputExtensionsFromString(postOutputExtensionsStr)):
            self.dialog.statusLabel.setText(f'The specified post output extensions are not valid. Known extensions: {", ".join(RenderingPipelineUtil.KnownPostOutputExtensions)}')
            return

        # Verify naming:
        namings = [(sidNaming, 'SID'), (renderSceneNaming, 'Render Scene'), (inputSceneNaming, 'Input Scene'), (environmentSceneNaming, 'Environment Scene'),
                   (nukeSceneNaming, 'Nuke Scene'), (renderingNaming, 'Rendering'), (postNaming, 'Post'), (deliveryNaming, 'Delivery')]

        if not all([self.verifyNamingConvention(nc, ncn) for nc, ncn in namings]):
            return

        environment = Environment(envId)
        pipeline = self.renderingPipelineManager.constructPipeline(pipelineName, pipelineClassName)

        environment.settings[PipelineKeys.BaseFolder] = baseProjectFolder
        environment.settings[PipelineKeys.PipelineType] = pipelineType
        environment.settings[PipelineKeys.PipelineClass] = pipelineClassName
        environment.settings[PipelineKeys.RenderSceneCreationScript] = renderSceneCreationScript
        environment.settings[PipelineKeys.InputSceneCreationScript] = inputSceneCreationScript
        environment.settings[PipelineKeys.NukeScript] = nukeScript
        environment.settings[PipelineKeys.ProductTable] = productTable
        environment.settings[PipelineKeys.ProductTableSheetName] = sheetName
        environment.settings[PipelineKeys.BaseScene] = baseScene
        environment.settings[PipelineKeys.RenderSettings] = renderSettingsFile
        environment.settings[PipelineKeys.ReplaceGermanCharacters] = replaceGermanChars
        environment.settings[PipelineKeys.RenderingExtension] = renderingExtension
        environment.settings[PipelineKeys.PostOutputExtensions] = postOutputExtensionsStr
        environment.settings[PipelineKeys.PerspectiveCodes] = perspectiveCodesStr

        environment.settings[PipelineKeys.SidNaming] = sidNaming
        environment.settings[PipelineKeys.RenderSceneNaming] = renderSceneNaming
        environment.settings[PipelineKeys.InputSceneNaming] = inputSceneNaming
        environment.settings[PipelineKeys.EnvironmentSceneNaming] = environmentSceneNaming
        environment.settings[PipelineKeys.NukeSceneNaming] = nukeSceneNaming
        environment.settings[PipelineKeys.RenderingNaming] = renderingNaming
        environment.settings[PipelineKeys.PostNaming] = postNaming
        environment.settings[PipelineKeys.DeliveryNaming] = deliveryNaming
        environment.settings[PipelineKeys.SceneExtension] = self.getSceneExtensionFromPipelineType(pipelineType)

        for envEntry in self.environmentEntries:
            if envEntry.isApplicable():
                envEntry.saveValue(environment)

        # Setup and create folders by pipeline (scenes [render,input], renderings, post, delivery)
        # Set relative defaults for these folders. If relative -> save in db otherwise this is pipeline specific and the old default stays in db.
        projectSubfolderSaveDict = self.projectSubfolderDict.copy()
        def setupProjectSubfolder(key: str, folder: str):
            fullpath = folder
            if not os.path.isabs(folder):
                fullpath = os.path.join(baseProjectFolder, folder)
                base = '${' + PipelineKeys.BaseFolder + '}'
                environment.settings[key] = os.path.normpath(fullpath).replace(os.path.normpath(baseProjectFolder), base).replace('\\', '/')

                projectSubfolderSaveDict[key] = folder

            os.makedirs(fullpath, exist_ok=True)
            
        try:
            setupProjectSubfolder(PipelineKeys.RenderScenesFolder, renderScenesFolder)
            setupProjectSubfolder(PipelineKeys.InputScenesFolder, inputScenesFolder)
            setupProjectSubfolder(PipelineKeys.EnvironmentScenesFolder, environmentScenesFolder)
            setupProjectSubfolder(PipelineKeys.NukeScenesFolder, nukeScenesFolder)
            setupProjectSubfolder(PipelineKeys.RenderingsFolder, renderingsFolder)
            setupProjectSubfolder(PipelineKeys.PostFolder, postFolder)
            setupProjectSubfolder(PipelineKeys.DeliveryFolder, deliveryFolder)
        except Exception as e:
            self.dialog.statusLabel.setText(f'Failed to create subfolders: {str(e)}')
            return

        # Read the table:
        try:
            progressDialog = ProgressDialog()
            progressDialog.open()
            pipeline.readProductTable(productTablePath=productTable, productTableSheetname=sheetName, environmentSettings=environment.getEvaluatedSettings(), onProgressUpdate=progressDialog.updateProgress)
        except Exception as e:
            progressDialog.close()
            self.dialog.statusLabel.setText(f'Failed reading the product table {productTable} with exception: {str(e)}')
            return

        pipelineExists = self.renderingPipelineManager.getPipelineFromName(pipelineName) != None

        self.renderingPipelineManager.addNewPipelineInstance(pipeline, replaceExisting=True)
        self.environmentManager.addEnvironment(environment, save=True, replaceExisting=True)
        if projectSubfolderSaveDict != self.projectSubfolderDict:
            self.renderingPipelineManager.saveProjectSubfolders(projectSubfolderSaveDict)

        self.viewerRegistry.environmentManagerViewer.refreshEnvironmentsComboBox()
        self.viewerRegistry.collectionViewer.refreshCollections()
        self.refreshAvailablePipelineMenu()

        if not pipelineExists:
            self.selectPipelineFromName(pipelineName)
            self.hide()
        else:
            self.viewerRegistry.documentSearchFilterViewer.viewItems(saveSearchHistoryEntry=False)

    def onPipelineNameChanged(self, pipelineName: str):
        if pipelineName in self.renderingPipelineManager.pipelineNames:
            self.loadPipeline(pipelineName)
            self.dialog.createButton.setText(' Modify')
            self.dialog.deleteButton.setVisible(True)
        else:
            self.dialog.createButton.setText(' Create')
            self.dialog.deleteButton.setVisible(False)

    def refreshProductSheetNameComboBox(self):
        self.dialog.productTableSheetNameComboBox.clear()
        productTablePath = self.dialog.productTableEdit.text()

        sheetNames = table_util.getSheetNames(productTablePath)
        if sheetNames:
            for sheetName in sheetNames:
                self.dialog.productTableSheetNameComboBox.addItem(sheetName)

    def onProductTableSheetNameChanged(self, txt: str):
        self.updateExtractedTableHeader()

    def onProductTableChanged(self, productTablePath: str):
        self.updateExtractedTableHeader()
        self.refreshProductSheetNameComboBox()

    def updateExtractedTableHeader(self):
        productTablePath = self.dialog.productTableEdit.text()
        sheetName = self.dialog.productTableSheetNameComboBox.currentText()
        table: QtWidgets.QTableWidget = self.dialog.extractedProductTableWidget
        table.clear()
        
        if os.path.exists(productTablePath):
            try:
                productTable = table_util.readTable(productTablePath,excelSheetName=sheetName)
                header = productTable.getHeader()
                
                table.setColumnCount(len(header))
                table.setHorizontalHeaderLabels(header)
                self.currentHeader = header
            except:
                pass

    def stripBaseFolder(self, v: str):
        base = '${' + PipelineKeys.BaseFolder + '}'
        if v.startswith(base):
            return v.lstrip(base).lstrip('/').lstrip('\\')

        return v

    def loadPipeline(self, pipelineName: str):
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        environment = self.environmentManager.getEnvironmentFromName(pipeline.environmentName)
        if not environment:
            environment = Environment('')

        environmentSettings = environment.settings

        if pipeline:
            self.dialog.baseProjectFolderEdit.setText(environmentSettings.get(PipelineKeys.BaseFolder, ''))
            self.dialog.pipelineTypeComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineType, ''))
            self.dialog.pipelineClassComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineClass, ''))
            self.dialog.renderSceneCreationScriptEdit.setText(environmentSettings.get(PipelineKeys.RenderSceneCreationScript, ''))
            self.dialog.inputSceneCreationScriptEdit.setText(environmentSettings.get(PipelineKeys.InputSceneCreationScript, ''))
            self.dialog.nukeScriptEdit.setText(environmentSettings.get(PipelineKeys.NukeScript, ''))
            self.dialog.productTableEdit.setText(environmentSettings.get(PipelineKeys.ProductTable, ''))
            self.dialog.productTableSheetNameComboBox.setCurrentText(environmentSettings.get(PipelineKeys.ProductTableSheetName, ''))
            self.dialog.baseSceneEdit.setText(environmentSettings.get(PipelineKeys.BaseScene, ''))
            self.dialog.renderSettingsEdit.setText(environmentSettings.get(PipelineKeys.RenderSettings, ''))
            self.dialog.replaceGermanCharactersCheckBox.setChecked(environmentSettings.get(PipelineKeys.ReplaceGermanCharacters, True))
            self.dialog.perspectiveCodesEdit.setText(environmentSettings.get(PipelineKeys.PerspectiveCodes, ''))
            self.dialog.renderingExtensionComboBox.setCurrentText(environmentSettings.get(PipelineKeys.RenderingExtension, ''))
            self.dialog.postOutputExtensionsEdit.setText(environmentSettings.get(PipelineKeys.PostOutputExtensions, ''))

            self.dialog.renderScenesFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.RenderScenesFolder, '')))
            self.dialog.inputScenesFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.InputScenesFolder, '')))
            self.dialog.environmentScenesEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.EnvironmentScenesFolder, '')))
            self.dialog.nukeScenesFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.NukeScenesFolder, '')))
            self.dialog.renderingsFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.RenderingsFolder, '')))
            self.dialog.postFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.PostFolder, '')))
            self.dialog.deliveryFolderEdit.setText(self.stripBaseFolder(environmentSettings.get(PipelineKeys.DeliveryFolder, '')))

            self.dialog.sidNamingEdit.setText(environmentSettings.get(PipelineKeys.SidNaming, ''))
            self.dialog.renderSceneNamingEdit.setText(environmentSettings.get(PipelineKeys.RenderSceneNaming, ''))
            self.dialog.inputSceneNamingEdit.setText(environmentSettings.get(PipelineKeys.InputSceneNaming, ''))
            self.dialog.nukeSceneNamingEdit.setText(environmentSettings.get(PipelineKeys.NukeSceneNaming, ''))
            self.dialog.environmentSceneNamingEdit.setText(environmentSettings.get(PipelineKeys.EnvironmentSceneNaming, ''))
            self.dialog.renderingNamingEdit.setText(environmentSettings.get(PipelineKeys.RenderingNaming, ''))
            self.dialog.postNamingEdit.setText(environmentSettings.get(PipelineKeys.PostNaming, ''))
            self.dialog.deliveryNamingEdit.setText(environmentSettings.get(PipelineKeys.DeliveryNaming, ''))

            self.dialog.headerConfirmationCheckBox.setChecked(True)

            for envEntry in self.environmentEntries:
                if envEntry.isApplicable():
                    envEntry.loadValue(environment)

    @property
    def knownPipelineTypes(self) -> List[str]:
        return [t.value for t in PipelineType]

    def getSceneExtensionFromPipelineType(self, pipelineType: PipelineType):
        pipelineType = PipelineType(pipelineType)

        if pipelineType == PipelineType.Max3ds:
            return 'max'
        elif pipelineType == PipelineType.Blender:
            return 'blend'

        return None

    def setupPipelineTypeComboBox(self):
        cb: QtWidgets.QComboBox = self.dialog.pipelineTypeComboBox
        cb.clear()
        for pipelineType in self.knownPipelineTypes:
            cb.addItem(pipelineType)

        cb.currentTextChanged.connect(self.onPipelineTypeChanged)

    def onPipelineTypeChanged(self, text: str):
        self.updateTabs()

    def updateTabs(self):
        pipelineType = PipelineType(self.dialog.pipelineTypeComboBox.currentText())
        tabWidget: QtWidgets.QTabWidget = self.dialog.tabWidget

        if pipelineType == PipelineType.Max3ds:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.blenderTab))
            tabWidget.addTab(self.dialog.max3dsTab, '3dsMax')
        elif pipelineType == PipelineType.Blender:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.max3dsTab))
            tabWidget.addTab(self.dialog.blenderTab, 'Blender')

    def updatePipelineClassComboBox(self):
        cb: QtWidgets.QComboBox = self.dialog.pipelineClassComboBox
        cb.clear()
        for className in self.renderingPipelineManager.pipelineClassNames:
            cb.addItem(className)

    def show(self):
        self.generateNukeSourceCodeTemplate()
        self.generateMaxSourceCodeTemplate(MaxSourceTemplateSceneType.InputScene)
        self.generateMaxSourceCodeTemplate(MaxSourceTemplateSceneType.RenderScene)
        self.refreshPipelineNameComboBox()
        self.dialog.show()

    def hide(self):
        self.dialog.hide()

    def addCodeLine(self, edit: QtWidgets.QTextEdit, codeLine: str, tabs=0):
        edit.append(f'{" "*tabs*4}{codeLine}')

    def generateNukeSourceCodeTemplate(self):
        edit: QtWidgets.QTextEdit = self.dialog.nukeSourceCodeTemplateEdit

        edit.clear()

        self.addCodeLine(edit, 'import nuke, os\n')

        self.addCodeLine(edit, 'class Environment:')
        self.addCodeLine(edit, 'def __init__(self, infoDict):', tabs=1)
        self.addCodeLine(edit, 'self.infoDict = infoDict\n', tabs=2)

        for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
            value = getattr(PipelineKeys, key)

            self.addCodeLine(edit, f'def {key}(self):', tabs=1)
            self.addCodeLine(edit, f'return self.infoDict.get("{value}")', tabs=2)
            self.addCodeLine(edit, '')

        self.addCodeLine(edit, f'def getRenderingFilename(self):', tabs=1)
        self.addCodeLine(edit, f'return self.RenderingFilename().replace("\\\\", "/")\n', tabs=2)

        self.addCodeLine(edit, f'def getPostOutputExtensions(self):', tabs=1)
        self.addCodeLine(edit, f'return [ext.strip().lower() for ext in self.PostOutputExtensions().split(",")]\n', tabs=2)

        self.addCodeLine(edit, f'def getPostFilename(self, ext):', tabs=1)
        self.addCodeLine(edit, f'return self.PostFilename().replace("\\\\", "/") + "." + ext\n', tabs=2)

        self.addCodeLine(edit, '')
        self.addCodeLine(edit, 'def process(infoDict):')
        self.addCodeLine(edit, 'env = Environment(infoDict)\n', tabs=1)
        
        self.addCodeLine(edit, '# Set read node file:', tabs=1)
        self.addCodeLine(edit, 'readNodeName = "Read"', tabs=1)
        self.addCodeLine(edit, f'readNode = nuke.toNode(readNodeName)\n', tabs=1)
        self.addCodeLine(edit, f'if not readNode:', tabs=1)
        self.addCodeLine(edit, f'raise RuntimeError("Could not find " + readNodeName + " node.")\n', tabs=2)

        self.addCodeLine(edit, 'renderingFilename = env.getRenderingFilename()\n', tabs=1)
        self.addCodeLine(edit, 'if not os.path.exists(renderingFilename):', tabs=1)
        self.addCodeLine(edit, 'raise RuntimeError("Could not find rendering " + renderingFilename)\n', tabs=2)

        self.addCodeLine(edit, f'readNode["file"].setValue(renderingFilename)\n', tabs=1)

        # Setup write node:
        self.addCodeLine(edit, 'writeNodeName = "Write"', tabs=1)
        self.addCodeLine(edit, f'writeNode = nuke.toNode(writeNodeName)\n', tabs=1)
        self.addCodeLine(edit, f'if not writeNode:', tabs=1)
        self.addCodeLine(edit, f'raise RuntimeError("Could not find " + writeNodeName + " node.")\n', tabs=2)

        self.addCodeLine(edit, '# Set write node files:', tabs=1)
        self.addCodeLine(edit, f'for ext in env.getPostOutputExtensions():', tabs=1)
        self.addCodeLine(edit, f'filename = env.getPostFilename(ext)', tabs=2)
        self.addCodeLine(edit, f'writeNode["file"].setValue(filename)\n', tabs=2)
        self.addCodeLine(edit, f'nuke.execute(writeNode, 1, 1)', tabs=2)

    def generateMaxSourceCodeTemplate(self, sceneType: MaxSourceTemplateSceneType):
        if sceneType == MaxSourceTemplateSceneType.InputScene:
            edit: QtWidgets.QTextEdit = self.dialog.maxInputSceneSourceCodeTemplateEdit
        elif sceneType == MaxSourceTemplateSceneType.RenderScene:
            edit: QtWidgets.QTextEdit = self.dialog.maxRenderSceneSourceCodeTemplateEdit
                
        self.addCodeLine(edit, 'global INFO_MAP = undefined')
        self.addCodeLine(edit, '')
        self.addCodeLine(edit, 'fn readInfoMap infoFile = (')
        self.addCodeLine(edit, '    py_main = Python.Import "__builtin__"')
        self.addCodeLine(edit, '    json = Python.Import "json"')
        self.addCodeLine(edit, '    ')
        self.addCodeLine(edit, '    f = py_main.open infoFile')
        self.addCodeLine(edit, '    infoMap = json.load f')
        self.addCodeLine(edit, '    f.close()')
        self.addCodeLine(edit, '    ')
        self.addCodeLine(edit, '    infoMap')
        self.addCodeLine(edit, ')')
        self.addCodeLine(edit, '')
        self.addCodeLine(edit, 'fn saveMaxFileChecked filename = (')
        self.addCodeLine(edit, '    if not (saveMaxFile filename) do throw ("Failed to save max file to " + filename as string)')
        self.addCodeLine(edit, ')')
        self.addCodeLine(edit, '')

        self.addCodeLine(edit, 'fn initInfoMapGlobals = (')
        for key in [item for item in dir(PipelineKeys) if not item.startswith("__")]:
            value = getattr(PipelineKeys, key)
            self.addCodeLine(edit, f'   global {key} = INFO_MAP["{value}"]')
        self.addCodeLine(edit, ')')
        
        self.addCodeLine(edit, '')
        self.addCodeLine(edit, 'fn executePipelineRequest infoFile = (')
        self.addCodeLine(edit, '    global INFO_MAP')
        self.addCodeLine(edit, '    ')
        self.addCodeLine(edit, '    INFO_MAP = readInfoMap infoFile')
        self.addCodeLine(edit, '    initInfoMapGlobals()')
        self.addCodeLine(edit, '    ')
        self.addCodeLine(edit, '    -- Prepare')
        self.addCodeLine(edit, '    loadedBaseSceneFile = loadMaxFile baseFile useFileUnits:true')
        self.addCodeLine(edit, '    if not loadedBaseSceneFile do throw ("Failed to load base scene file: " + BaseSceneFilename as string)')
        self.addCodeLine(edit, '    ')

        if sceneType == MaxSourceTemplateSceneType.RenderScene:
            self.addCodeLine(edit, '    -- Merge environment scene file if available')
            self.addCodeLine(edit, '    if EnvironmentSceneNaming != "" do (')
            self.addCodeLine(edit, '        mergedEnvSceneFile = mergeMAXFile EnvironmentSceneFilename #mergeDups #useMergedMtlDups #neverReparent')
            self.addCodeLine(edit, '        if not mergedEnvSceneFile do throw ("Failed to merge env scene file: " + EnvironmentSceneFilename as string)')
            self.addCodeLine(edit, '    )')
            self.addCodeLine(edit, '    ')

        if sceneType == MaxSourceTemplateSceneType.RenderScene:
            self.addCodeLine(edit, '    -- Merge input scene file')
            self.addCodeLine(edit, '    mergedInputSceneFile = mergeMAXFile InputSceneFilename #mergeDups #useMergedMtlDups #neverReparent')
            self.addCodeLine(edit, '    if not mergedInputSceneFile do throw ("Failed to merge input scene file: " + InputSceneFilename as string)')
            self.addCodeLine(edit, '    ')

        self.addCodeLine(edit, '    /*******************************************************')
        self.addCodeLine(edit, '    TODO: Apply variation logic')
        self.addCodeLine(edit, '    ********************************************************/')
        self.addCodeLine(edit, '    ')
        self.addCodeLine(edit, f'    saveMaxFileChecked {"InputSceneFilename" if sceneType == MaxSourceTemplateSceneType.InputScene else "RenderSceneFilename"}')
        self.addCodeLine(edit, ')')