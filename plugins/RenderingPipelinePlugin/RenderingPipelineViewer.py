from ServiceRegistry import ServiceRegistry
from MetadataManagerCore import Keys
from typing import List

from RenderingPipelinePlugin.PipelineType import PipelineType
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager
import asset_manager
from qt_extensions import qt_util
from PySide2 import QtWidgets
from MetadataManagerCore.environment.Environment import Environment
import os
import xlrd
import logging
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
from VisualScriptingExtensions.third_party_extensions.deadline_nodes import getDeadlinePoolNames
from MetadataManagerCore.threading import threading_util
from viewers.ViewerRegistry import ViewerRegistry

logger = logging.getLogger(__name__)

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
    def __init__(self, parentWindow, renderingPipelineManager: RenderingPipelineManager, serviceRegistry: ServiceRegistry, viewerRegistry: ViewerRegistry):
        super().__init__()
        
        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "renderingPipeline.ui")
        self.dialog = asset_manager.loadDialogAbsolutePath(uiFilePath, fixedSize=False)

        self.serviceRegistry = serviceRegistry
        self.viewerRegistry = viewerRegistry
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
        self.dialog.cancelButton.clicked.connect(self.hide)

        self.refreshPipelineNameComboBox()
        self.dialog.pipelineNameComboBox.currentTextChanged.connect(self.onPipelineNameChanged)
        self.dialog.productTableEdit.textChanged.connect(self.onProductTableEditTextChanged)
        self.dialog.productTableSheetNameEdit.textChanged.connect(self.onProductTableEditTextChanged)

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

    def onPipelineSelected(self, pipelineName: str):
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        if pipeline:
            self.viewerRegistry.collectionViewer.showSingleCollection(pipeline.dbCollectionName)
            self.viewerRegistry.environmentManagerViewer.setCurrentEnvironment(pipeline.environment)
            self.viewerRegistry.documentSearchFilterViewer.viewItems(saveSearchHistoryEntry=False)
            self.pipelineSelectionMenu.setTitle(f'Selected RP: {pipelineName}')

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

    def onCreateClick(self):
        pipelineName = self.dialog.pipelineNameComboBox.currentText()

        envId = self.environmentManager.getIdFromEnvironmentName(pipelineName)
        if pipelineName in self.renderingPipelineManager.pipelineNames or not self.environmentManager.isValidEnvironmentId(envId) or self.environmentManager.hasEnvironmentId(envId):
            self.dialog.statusLabel.setText(f'The pipeline {pipelineName} already exists or is invalid. Please type in a different name.')
            return

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
        sheetName = self.dialog.productTableSheetNameEdit.text()
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

        if not baseProjectFolder or not os.path.isabs(baseProjectFolder) or not os.path.exists(baseProjectFolder):
            self.dialog.statusLabel.setText(f'Please specify an existing base project folder.')
            return

        if not os.path.exists(productTable):
            self.dialog.statusLabel.setText(f'Please specify a valid product table path.')
            return

        if not RenderingPipelineUtil.validatePostOutputExtensions(RenderingPipelineUtil.extractPostOutputExtensionsFromString(postOutputExtensionsStr)):
            self.dialog.statusLabel.setText(f'The specified post output extensions are not valid. Known extensions: {", ".join(RenderingPipelineUtil.KnownPostOutputExtensions)}')
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
                environment.settings[key] = os.path.normpath(fullpath).replace(os.path.normpath(baseProjectFolder), '${base_folder}').replace('\\', '/')

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
        # TODO: Need progress bar.
        try:
            pipeline.readProductTable(productTablePath=productTable, productTableSheetname=sheetName, environmentSettings=environment.getEvaluatedSettings())
        except Exception as e:
            self.dialog.statusLabel.setText(f'Failed reading the product table {productTable} with exception: {str(e)}')
            return

        self.renderingPipelineManager.addNewPipelineInstance(pipeline)
        self.environmentManager.addEnvironment(environment, save=True)
        if projectSubfolderSaveDict != self.projectSubfolderDict:
            self.renderingPipelineManager.saveProjectSubfolders(projectSubfolderSaveDict)

        self.viewerRegistry.environmentManagerViewer.refreshEnvironmentsComboBox()
        self.viewerRegistry.collectionViewer.refreshCollections()
        self.refreshAvailablePipelineMenu()
        self.hide()

    def onPipelineNameChanged(self, pipelineName: str):
        if pipelineName in self.renderingPipelineManager.pipelineNames:
            self.loadPipeline(pipelineName)

    def onProductTableEditTextChanged(self, _: str):
        productTable = self.dialog.productTableEdit.text()
        sheetName = self.dialog.productTableSheetNameEdit.text()
        table: QtWidgets.QTableWidget = self.dialog.extractedProductTableWidget
        table.clear()

        if os.path.exists(productTable):
            try:
                if productTable.endswith('.xlsx'):
                    sheet = xlrd.open_workbook(filename=productTable).sheet_by_name(sheetName)
                    header = sheet.row_values(0)
                elif productTable.endswith('.csv'):
                    with open(productTable) as f:
                        for row in f:
                            header = row.split(';')
                            break
                else:
                    raise RuntimeError(f'Unsupported file format {os.path.splitext(productTable)[1]}')
                
                table.setColumnCount(len(header))
                table.setHorizontalHeaderLabels(header)
                self.currentHeader = header
            except:
                pass

    def stripBaseFolder(self, v: str):
        if v.startswith('${base_folder}'):
            return v.lstrip('${base_folder}').lstrip('/').lstrip('\\')

        return v

    def loadPipeline(self, pipelineName: str):
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        environment = self.environmentManager.getEnvironmentFromName(pipeline.environmentName)
        environmentSettings = environment.settings

        if pipeline:
            self.dialog.baseProjectFolderEdit.setText(environmentSettings.get(PipelineKeys.BaseFolder, ''))
            self.dialog.pipelineTypeComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineType, ''))
            self.dialog.pipelineClassComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineClass, ''))
            self.dialog.renderSceneCreationScriptEdit.setText(environmentSettings.get(PipelineKeys.RenderSceneCreationScript, ''))
            self.dialog.inputSceneCreationScriptEdit.setText(environmentSettings.get(PipelineKeys.InputSceneCreationScript, ''))
            self.dialog.nukeScriptEdit.setText(environmentSettings.get(PipelineKeys.NukeScript, ''))
            self.dialog.productTableEdit.setText(environmentSettings.get(PipelineKeys.ProductTable, ''))
            self.dialog.productTableSheetNameEdit.setText(environmentSettings.get(PipelineKeys.ProductTableSheetName, ''))
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
        self.dialog.show()

    def hide(self):
        self.dialog.hide()