import PySide2
from table import table_util
from qt_extensions.InputConfirmDialog import InputConfirmDialog
from AppInfo import AppInfo
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from RenderingPipelinePlugin.filters.MappingFilter import MappingFilter
from ServiceRegistry import ServiceRegistry
from MetadataManagerCore import Keys
from typing import Dict, List

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
from RenderingPipelinePlugin import SourceCodeTemplateGeneration
from RenderingPipelinePlugin.SourceCodeTemplateGeneration import SourceCodeTemplateSceneType

logger = logging.getLogger(__name__)

def connectRelativeProjectFolderSelection(dialog, lineEdit: QtWidgets.QLineEdit, button: QtWidgets.QPushButton, initialDir=""):
    def onSelect():
        dirName = QtWidgets.QFileDialog.getExistingDirectory(dialog, "Open", initialDir)
        if dirName != None and dirName != "":
            baseProjectFolder = dialog.baseProjectFolderEdit.text()
            if os.path.normpath(dirName).startswith(os.path.normpath(baseProjectFolder)):
                dirName = os.path.relpath(dirName, baseProjectFolder)

            lineEdit.setText(dirName)
    
    button.clicked.connect(onSelect)

def stripBaseFolder(v: str):
    base = '${' + PipelineKeys.BaseFolder + '}'
    if v.startswith(base):
        return v.lstrip(base).lstrip('/').lstrip('\\')

    return v

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

    def verify(self):
        pass

class LineEditEnvironmentEntry(EnvironmentEntry):
    def __init__(self, envKey: str, widget: QtWidgets.QWidget, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None, regexPattern = None) -> None:
        super().__init__(envKey, widget, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox)

        self.regexPattern = regexPattern

    def saveValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        environment.settings[self.envKey] = edit.text()

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(environment.settings.get(self.envKey))

    def verify(self):
        if self.regexPattern:
            valid = re.search(self.regexPattern, self.widget.text()) != None

            if not valid:
                raise RuntimeError(f'The text of {self.envKey} is not valid. The supported format is: {self.regexPattern}')

class CheckBoxEnvironmentEntry(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        checkbox: QtWidgets.QCheckBox = self.widget
        environment.settings[self.envKey] = checkbox.isChecked()

    def loadValue(self, environment: Environment):
        checkbox: QtWidgets.QCheckBox = self.widget
        checkbox.setChecked(environment.settings.get(self.envKey, False))

class ComboBoxEnvironmentEntry(EnvironmentEntry):
    def saveValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        environment.settings[self.envKey] = cb.currentText()

    def loadValue(self, environment: Environment):
        cb: QtWidgets.QComboBox = self.widget
        cb.setCurrentText(environment.settings.get(self.envKey))

class NamingEnvironmentEntry(LineEditEnvironmentEntry):
    def saveValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        environment.settings[self.envKey] = edit.text()

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(environment.settings.get(self.envKey))

    def verify(self):
        namingRegexPattern = '^([\w\d# /\-]*(\[[\w\d# /\-]*\])*)*$'
        namingConvention = self.widget.text()
        valid = re.search(namingRegexPattern, namingConvention) != None

        if not valid:
            raise RuntimeError(f'The naming convetion for {self.envKey} is not valid.')

class ProjectSubFolderEnvironmentEntry(LineEditEnvironmentEntry):
    def __init__(self, envKey: str, lineEdit: QtWidgets.QLineEdit, renderingPipelineViewer, 
                 folderSelectButton: QtWidgets.QPushButton, pipelineType: PipelineType = None, pipelineComboBox: QtWidgets.QComboBox = None) -> None:
        super().__init__(envKey, lineEdit, pipelineType=pipelineType, pipelineComboBox=pipelineComboBox)

        connectRelativeProjectFolderSelection(renderingPipelineViewer.dialog, lineEdit, folderSelectButton)

        self.renderingPipelineViewer = renderingPipelineViewer

    def saveValue(self, environment: Environment):
        baseProjectFolder = self.renderingPipelineViewer.dialog.baseProjectFolderEdit.text()
        folder = self.widget.text()
        fullpath = folder
        if os.path.isabs(fullpath):
            environment.settings[self.envKey] = fullpath.replace('\\', '/')
        else:
            fullpath = os.path.join(baseProjectFolder, folder)
            base = '${' + PipelineKeys.BaseFolder + '}'
            environment.settings[self.envKey] = os.path.normpath(fullpath).replace(os.path.normpath(baseProjectFolder), base).replace('\\', '/')

        try:
            os.makedirs(fullpath, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f'Failed to create subfolder for key {self.envKeys}: {str(e)}')

    def loadValue(self, environment: Environment):
        edit: QtWidgets.QLineEdit = self.widget
        edit.setText(stripBaseFolder(environment.settings.get(self.envKey, '')))

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
        self.initIconMap()

        if self.iconMap.get('Deadline'):
            self.dialog.tabWidget.setTabIcon(self.dialog.tabWidget.indexOf(self.dialog.deadlineTab), self.iconMap.get('Deadline'))

        if self.iconMap.get('Nuke'):
            self.dialog.tabWidget.setTabIcon(self.dialog.tabWidget.indexOf(self.dialog.nukeTab), self.iconMap.get('Nuke'))

        self.updatePipelineClassComboBox()
        self.setupPipelineTypeComboBox()
        self.dialog.pipelineTypeComboBox.setCurrentText(PipelineType.Blender.value)

        self.dialog.createButton.clicked.connect(self.onCreateClick)
        self.dialog.deleteButton.clicked.connect(self.onDeleteClick)
        self.dialog.cancelButton.clicked.connect(self.hide)

        self.dialog.deleteButton.setVisible(False)

        self.refreshPipelineNameComboBox()
        self.dialog.nukeVersionComboBox.setCurrentText('12.0')
        self.dialog.pipelineNameComboBox.currentTextChanged.connect(self.onPipelineNameChanged)
        self.dialog.productTableEdit.textChanged.connect(self.onProductTableChanged)
        self.dialog.productTableSheetNameComboBox.currentTextChanged.connect(self.onProductTableSheetNameChanged)
        self.dialog.copyToClipboardButton.clicked.connect(lambda: QtGui.QGuiApplication.clipboard().setText(self.dialog.nukeSourceCodeTemplateEdit.toPlainText()))

        self.dialog.statusLabel.setText('')
        self.dialog.statusLabel.setStyleSheet('color: red')

        self.dialog.pipelineNameComboBox.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_ ]*$'))
        self.dialog.perspectiveCodesEdit.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_ ,]*$'))
        self.dialog.sidNamingEdit.setValidator(RegexPatternInputValidator('^[a-zA-Z0-9_\-/ \]\[]*$'))
        
        self.currentHeader = []
        
        qt_util.connectFolderSelection(self.dialog, self.dialog.baseProjectFolderEdit, self.dialog.baseProjectFolderButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.renderSceneCreationScriptEdit, self.dialog.renderSceneCreationScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.inputSceneCreationScriptEdit, self.dialog.inputSceneCreationScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.nukeScriptEdit, self.dialog.nukeScriptButton)
        qt_util.connectFileSelection(self.dialog, self.dialog.productTableEdit, self.dialog.productTableButton, filter='Table File (*.xlsx;*.xls;*.csv)')
        qt_util.connectFileSelection(self.dialog, self.dialog.renderSettingsEdit, self.dialog.renderSettingsButton)

        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlinePriority, self.dialog.deadlinePriorityEdit))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.Max3dsVersion, self.dialog.versionOf3dsMaxComboBox, PipelineType.Max3ds, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.BlenderVersion, self.dialog.blenderVersionComboBox, PipelineType.Blender, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.NukeVersion, self.dialog.nukeVersionComboBox))

        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlineInputSceneTimeout, self.dialog.inputSceneDeadlineTimeout))
        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlineRenderSceneTimeout, self.dialog.renderSceneDeadlineTimeout))
        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlineRenderingTimeout, self.dialog.renderingDeadlineTimeout))
        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlineNukeTimeout, self.dialog.nukeDeadlineTimeout))
        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlineDeliveryTimeout, self.dialog.deliveryDeadlineTimeout))

        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.BaseScenesFolder, self.dialog.baseScenesFolderEdit, self, self.dialog.baseScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.InputScenesFolder, self.dialog.inputScenesFolderEdit, self, self.dialog.inputScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.RenderScenesFolder, self.dialog.renderScenesFolderEdit, self, self.dialog.renderScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.EnvironmentScenesFolder, self.dialog.environmentScenesEdit, self, self.dialog.environmentScenesButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.NukeScenesFolder, self.dialog.nukeScenesFolderEdit, self, self.dialog.nukeScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.RenderingsFolder, self.dialog.renderingsFolderEdit, self, self.dialog.renderingsFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.PostFolder, self.dialog.postFolderEdit, self, self.dialog.postFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.DeliveryFolder, self.dialog.deliveryFolderEdit, self, self.dialog.deliveryFolderButton))

        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.BaseSceneNaming, self.dialog.baseSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.SidNaming, self.dialog.sidNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.RenderSceneNaming, self.dialog.renderSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.InputSceneNaming, self.dialog.inputSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.NukeSceneNaming, self.dialog.nukeSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.EnvironmentSceneNaming, self.dialog.environmentSceneNamingEdit))

        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.SaveRenderScene, self.dialog.saveRenderSceneCheckBox, PipelineType.Blender))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.RenderInSceneCreationScript, self.dialog.renderInSceneCreationScriptCheckBox, PipelineType.Blender))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.ApplyCameraFraming, self.dialog.applyCameraFramingCheckBox, PipelineType.Blender))

        self.perspectiveToNamingConventionEnvEntries: Dict[str,List[EnvironmentEntry]] = dict()

        self.dialog.perspectiveCodesEdit.editingFinished.connect(self.perspectiveCodesEditingFinished)

        threading_util.runInThread(self.fetchDeadlinePoolNames)

        self.refreshAvailablePipelineMenu()
        self.updateTabs()
        self.registerFilters()

        self.viewerRegistry.collectionViewer.refreshCollections()

    def perspectiveCodesEditingFinished(self):
        self.refreshPerspectiveTabWidget()

    def refreshPerspectiveTabWidget(self):
        perspectiveCodes = [code.strip() for code in self.dialog.perspectiveCodesEdit.text().split(',')]

        tabWidget : QtWidgets.QTabWidget = self.dialog.perspectiveTabWidget
        tabWidget.clear()

        # Remove tabs with missing perspectives:

        for tabIdx in range(tabWidget.count() - 1, -1, -1):
            tab = tabWidget.widget(tabIdx)
            if not tabWidget.tabText(tabIdx) in perspectiveCodes:
                perspectiveCode = tabWidget.tabText(tabIdx)
                tabWidget.removeTab(tabIdx)

                # Remove the naming convention entries
                for entry in self.perspectiveToNamingConventionEnvEntries[perspectiveCode]:
                    self.environmentEntries.remove(entry)

                del self.perspectiveToNamingConventionEnvEntries[perspectiveCode]

        perspectiveToTabMap = {tabWidget.tabText(tabIdx):tabWidget.widget(tabIdx) for tabIdx in range(tabWidget.count())}

        # Add missing tabs:
        for perspectiveCode in perspectiveCodes:
            if not perspectiveCode in perspectiveToTabMap:
                tab = QtWidgets.QWidget()
                tabWidget.addTab(tab, perspectiveCode)
                formLayout = QtWidgets.QFormLayout()
                tab.setLayout(formLayout)

                # Add the naming convention entries
                entries = [
                    (PipelineKeys.getKeyWithPerspective(PipelineKeys.RenderingNaming, perspectiveCode), 'Rendering Relative File Naming Convention'),
                    (PipelineKeys.getKeyWithPerspective(PipelineKeys.PostNaming, perspectiveCode), 'Post Relative File Naming Convention'),
                    (PipelineKeys.getKeyWithPerspective(PipelineKeys.DeliveryNaming, perspectiveCode), 'Delivery Relative File Naming Convention'),
                    (PipelineKeys.getKeyWithPerspective(PipelineKeys.Frames, perspectiveCode), 'Frames')]

                self.perspectiveToNamingConventionEnvEntries[perspectiveCode] = entries

                for envKey, labelText in entries:
                    edit = QtWidgets.QLineEdit()
                    formLayout.addRow(labelText, edit)

                    if labelText == 'Frames':
                        envEntry = LineEditEnvironmentEntry(envKey, edit)
                    else:
                        envEntry = NamingEnvironmentEntry(envKey, edit)
                    self.environmentEntries.append(envEntry)

    def initIconMap(self):
        deadlineRepoFolder = self.serviceRegistry.deadlineService.info.deadlineRepositoryLocation
        self.iconMap = dict()

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins', 'Blender', 'Blender.ico')):
            self.iconMap[PipelineType.Blender.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins', 'Blender', 'Blender.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins','3dsmax', '3dsmax.ico')):
            self.iconMap[PipelineType.Max3ds.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins','3dsmax', '3dsmax.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins', 'MayaBatch', 'MayaBatch.ico')):
            self.iconMap[PipelineType.Maya.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins', 'MayaBatch', 'MayaBatch.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins', 'Nuke', 'Nuke.ico')):
            self.iconMap['Nuke'] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins', 'Nuke', 'Nuke.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'settings', 'Thinkbox.ico')):
            self.iconMap['Deadline'] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'settings', 'Thinkbox.ico'))

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
            pipeline = self.renderingPipelineManager.getPipelineFromName(selectedPipelineName)
            if pipeline:
                self.viewerRegistry.environmentManagerViewer.setCurrentEnvironment(pipeline.environment)
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
        self.environmentEntries.append(ComboBoxEnvironmentEntry(envKey, comboBox))

        if poolNames:
            for poolName in poolNames:
                comboBox.addItem(poolName)

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

    def onCreateClick(self):
        pipelineName = self.dialog.pipelineNameComboBox.currentText()

        envId = self.environmentManager.getIdFromEnvironmentName(pipelineName)

        if self.dialog.updateCollectionCheckBox.isChecked() and not self.dialog.headerConfirmationCheckBox.isChecked():
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
        renderSettingsFile = self.dialog.renderSettingsEdit.text()
        replaceGermanChars = self.dialog.replaceGermanCharactersCheckBox.isChecked()
        perspectiveCodesStr = self.dialog.perspectiveCodesEdit.text()
        renderingExtension = self.dialog.renderingExtensionComboBox.currentText()
        postOutputExtensionsStr = self.dialog.postOutputExtensionsEdit.text()

        sidNaming = self.dialog.sidNamingEdit.text()

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

        if not perspectiveCodesStr:
            self.dialog.statusLabel.setText(f'At least one perspective code must be defined.')
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
        environment.settings[PipelineKeys.RenderSettings] = renderSettingsFile
        environment.settings[PipelineKeys.ReplaceGermanCharacters] = replaceGermanChars
        environment.settings[PipelineKeys.RenderingExtension] = renderingExtension
        environment.settings[PipelineKeys.PostOutputExtensions] = postOutputExtensionsStr
        environment.settings[PipelineKeys.PerspectiveCodes] = perspectiveCodesStr

        environment.settings[PipelineKeys.SceneExtension] = self.getSceneExtensionFromPipelineType(pipelineType)

        try:
            for envEntry in self.environmentEntries:
                if envEntry.isApplicable():
                    envEntry.verify()
                    envEntry.saveValue(environment)
        except Exception as e:
            self.dialog.statusLabel.setText(str(e))
            return

        # Read the table:
        if self.dialog.updateCollectionCheckBox.isChecked():
            try:
                pipelineExists = pipelineName in self.renderingPipelineManager.pipelineNames
                replaceExistingCollection = pipelineExists and self.dialog.replaceExistingCollectionCheckBox.isChecked()
                progressDialog = ProgressDialog()
                progressDialog.open()
                pipeline.readProductTable(productTablePath=productTable, productTableSheetname=sheetName, environmentSettings=environment.getEvaluatedSettings(), 
                                        onProgressUpdate=progressDialog.updateProgress, replaceExistingCollection=replaceExistingCollection)
            except Exception as e:
                progressDialog.close()
                self.dialog.statusLabel.setText(f'Failed reading the product table {productTable} with exception: {str(e)}')
                return

        pipelineExists = self.renderingPipelineManager.getPipelineFromName(pipelineName) != None

        self.renderingPipelineManager.addNewPipelineInstance(pipeline, replaceExisting=True)
        self.environmentManager.addEnvironment(environment, save=True, replaceExisting=True)

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
            self.dialog.updateCollectionCheckBox.setText('Update Table')
            self.dialog.deleteButton.setVisible(True)
            self.dialog.replaceExistingCollectionCheckBox.setVisible(True)
        else:
            self.dialog.createButton.setText(' Create')
            self.dialog.updateCollectionCheckBox.setText('Create Table')
            self.dialog.deleteButton.setVisible(False)
            self.dialog.replaceExistingCollectionCheckBox.setVisible(False)

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
        else:
            self.currentHeader = []

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
            self.dialog.renderSettingsEdit.setText(environmentSettings.get(PipelineKeys.RenderSettings, ''))
            self.dialog.replaceGermanCharactersCheckBox.setChecked(environmentSettings.get(PipelineKeys.ReplaceGermanCharacters, True))
            self.dialog.perspectiveCodesEdit.setText(environmentSettings.get(PipelineKeys.PerspectiveCodes, ''))
            self.dialog.renderingExtensionComboBox.setCurrentText(environmentSettings.get(PipelineKeys.RenderingExtension, ''))
            self.dialog.postOutputExtensionsEdit.setText(environmentSettings.get(PipelineKeys.PostOutputExtensions, ''))

            self.dialog.headerConfirmationCheckBox.setChecked(True)
            
            self.refreshPerspectiveTabWidget()
            
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
        elif pipelineType == PipelineType.Maya:
            return 'mb'

        return None

    def setupPipelineTypeComboBox(self):
        cb: QtWidgets.QComboBox = self.dialog.pipelineTypeComboBox
        cb.clear()
        for idx, pipelineType in enumerate(self.knownPipelineTypes):
            cb.addItem(pipelineType)

            iconFilename = self.iconMap.get(pipelineType)
            if iconFilename:
                cb.setItemIcon(idx, QtGui.QIcon(iconFilename))

        cb.currentTextChanged.connect(self.onPipelineTypeChanged)

    def onPipelineTypeChanged(self, text: str):
        self.updateTabs()
        SourceCodeTemplateGeneration.generateNukeSourceCodeTemplate(self.dialog.nukeSourceCodeTemplateEdit, self.selectedPipelineType)

    def updateTabs(self):
        pipelineType = PipelineType(self.dialog.pipelineTypeComboBox.currentText())
        tabWidget: QtWidgets.QTabWidget = self.dialog.tabWidget

        if pipelineType == PipelineType.Max3ds:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.blenderTab))
            tabWidget.addTab(self.dialog.max3dsTab, '3dsMax')

            if self.iconMap.get(PipelineType.Max3ds.value):
                tabWidget.setTabIcon(tabWidget.indexOf(self.dialog.max3dsTab), self.iconMap.get(PipelineType.Max3ds.value))
        elif pipelineType == PipelineType.Blender:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.max3dsTab))
            tabWidget.addTab(self.dialog.blenderTab, 'Blender')

            if self.iconMap.get(PipelineType.Blender.value):
                tabWidget.setTabIcon(tabWidget.indexOf(self.dialog.blenderTab), self.iconMap.get(PipelineType.Blender.value))

    def updatePipelineClassComboBox(self):
        cb: QtWidgets.QComboBox = self.dialog.pipelineClassComboBox
        cb.clear()
        for className in self.renderingPipelineManager.pipelineClassNames:
            cb.addItem(className)

    @property
    def selectedPipelineType(self):
        return PipelineType(self.dialog.pipelineTypeComboBox.currentText())

    def show(self):
        SourceCodeTemplateGeneration.generateNukeSourceCodeTemplate(self.dialog.nukeSourceCodeTemplateEdit, self.selectedPipelineType)
        SourceCodeTemplateGeneration.generateMaxSourceCodeTemplate(self.dialog.maxInputSceneSourceCodeTemplateEdit, SourceCodeTemplateSceneType.InputScene)
        SourceCodeTemplateGeneration.generateMaxSourceCodeTemplate(self.dialog.maxRenderSceneSourceCodeTemplateEdit, SourceCodeTemplateSceneType.RenderScene)
        SourceCodeTemplateGeneration.generateBlenderSourceCodeTemplate(self.dialog.blenderInputSceneSourceCodeTemplateEdit, SourceCodeTemplateSceneType.InputScene)
        SourceCodeTemplateGeneration.generateBlenderSourceCodeTemplate(self.dialog.blenderRenderSceneSourceCodeTemplateEdit, SourceCodeTemplateSceneType.RenderScene)
        self.dialog.pipelineNameComboBox.currentTextChanged.disconnect()
        self.refreshPipelineNameComboBox()
        self.dialog.pipelineNameComboBox.currentTextChanged.connect(self.onPipelineNameChanged)
        self.dialog.show()

    def hide(self):
        self.dialog.hide()