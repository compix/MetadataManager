import typing
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from MetadataManagerCore.third_party_integrations.deadline import deadline_service
from RenderingPipelinePlugin.CustomSubmissionTaskViewer import CustomSubmissionTaskViewer
from RenderingPipelinePlugin.EnvironmentEntry import CheckBoxEnvironmentEntry, ComboBoxEnvironmentEntry, DeadlinePoolComboBoxEnvironmentEntry, DeadlineTimeoutEnvironmentEntry, EnvironmentEntry, LineEditEnvironmentEntry, NamingEnvironmentEntry, ProjectFileEnvironmentEntry, ProjectSubFolderEnvironmentEntry
from RenderingPipelinePlugin.MetadataManagerTaskView import MetadataManagerTaskView
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from RenderingPipelinePlugin.TaskExecutionOrderView import TaskExecutionOrderView
from RenderingPipelinePlugin.submitters.SubmitterInfo import getOrderedSubmitterInfos
from RenderingPipelinePlugin.ui_elements import FileSelectionElement
from RenderingPipelinePlugin.unreal_engine import UnrealEnginePipelineKeys
from node_exec import windows_nodes
from viewers.EnvironmentViewer import EnvironmentViewer
from table import table_util
from qt_extensions.InputConfirmDialog import InputConfirmDialog
from AppInfo import AppInfo
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
import logging
from RenderingPipelinePlugin import PipelineKeys, RenderingPipelineUtil
from qt_extensions.RegexPatternInputValidator import RegexPatternInputValidator
from VisualScriptingExtensions.third_party_extensions.deadline_nodes import getDeadlinePoolNames
from MetadataManagerCore.threading import threading_util
from viewers.ViewerRegistry import ViewerRegistry
from enum import Enum
import re
from RenderingPipelinePlugin import SourceCodeTemplateGeneration
from RenderingPipelinePlugin.SourceCodeTemplateGeneration import SourceCodeTemplateSceneType, generateUnrealEngineMoviePipelineExecutorCode
from RenderingPipelinePlugin.RowSkipConditionUIElement import RowSkipConditionUIElement

logger = logging.getLogger(__name__)

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

        self.renderingPipelineManager.onPipelineClassRegistrationEvent.subscribe(lambda _: self.onPipelineClassRegistered())
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
        
        self.baseProjectFolderElement = FileSelectionElement(self.dialog, None, isFolder=True)
        self.formLayout: QtWidgets.QFormLayout = self.dialog.formLayout
        self.formLayout.insertRow(1, "Base Project Folder", self.baseProjectFolderElement.layout)
        self.inputSceneCreationScriptElement = FileSelectionElement(self.dialog, None)
        self.renderSceneCreationScriptElement = FileSelectionElement(self.dialog, None)
        self.nukeScriptElement = FileSelectionElement(self.dialog, None)
        self.blenderCompositingScriptElement = FileSelectionElement(self.dialog, None)
        self.renderSettingsElement = FileSelectionElement(self.dialog, None)

        self.formLayout.insertRow(6, "Input Scene Creation Script", self.inputSceneCreationScriptElement.layout)
        self.formLayout.insertRow(7, "Render Scene Creation Script", self.renderSceneCreationScriptElement.layout)
        self.formLayout.insertRow(8, "Nuke Script", self.nukeScriptElement.layout)
        self.formLayout.insertRow(10, "Blender Compositing Script", self.blenderCompositingScriptElement.layout)
        self.formLayout.insertRow(11, "Render Settings", self.renderSettingsElement.layout)

        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.BaseFolder, self.baseProjectFolderElement.edit))

        self.environmentEntries.append(ProjectFileEnvironmentEntry(PipelineKeys.InputSceneCreationScript, 
            self.inputSceneCreationScriptElement.edit, self, self.inputSceneCreationScriptElement.selectButton))

        self.environmentEntries.append(ProjectFileEnvironmentEntry(PipelineKeys.RenderSceneCreationScript, 
            self.renderSceneCreationScriptElement.edit, self, self.renderSceneCreationScriptElement.selectButton))

        self.environmentEntries.append(ProjectFileEnvironmentEntry(PipelineKeys.NukeScript, 
            self.nukeScriptElement.edit, self, self.nukeScriptElement.selectButton))

        self.environmentEntries.append(ProjectFileEnvironmentEntry(PipelineKeys.BlenderCompositingScript, 
            self.blenderCompositingScriptElement.edit, self, self.blenderCompositingScriptElement.selectButton))

        self.environmentEntries.append(ProjectFileEnvironmentEntry(PipelineKeys.RenderSettings, 
            self.renderSettingsElement.edit, self, self.renderSettingsElement.selectButton))

        self.productTableEnvEntry = ProjectFileEnvironmentEntry(PipelineKeys.ProductTable, self.dialog.productTableEdit, self,
            self.dialog.productTableButton, fileFilter='Table File (*.xlsx;*.xls;*.csv)')
        self.environmentEntries.append(self.productTableEnvEntry)

        self.environmentEntries.append(LineEditEnvironmentEntry(PipelineKeys.DeadlinePriority, self.dialog.deadlinePriorityEdit, valueType=int))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.Max3dsVersion, self.dialog.versionOf3dsMaxComboBox, PipelineType.Max3ds, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.BlenderVersion, self.dialog.blenderVersionComboBox, PipelineType.Blender, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.UnrealEngineVersion, self.dialog.unrealEngineVersionComboBox, PipelineType.UnrealEngine, self.dialog.pipelineTypeComboBox))
        self.environmentEntries.append(ComboBoxEnvironmentEntry(PipelineKeys.NukeVersion, self.dialog.nukeVersionComboBox))

        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineInputSceneTimeout, self.dialog.inputSceneDeadlineTimeout, valueType=int))
        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineRenderSceneTimeout, self.dialog.renderSceneDeadlineTimeout, valueType=int))
        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineRenderingTimeout, self.dialog.renderingDeadlineTimeout, valueType=int))
        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineNukeTimeout, self.dialog.nukeDeadlineTimeout, valueType=int))
        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineBlenderCompositingTimeout, self.dialog.blenderCompositingDeadlineTimeout, valueType=int))
        self.environmentEntries.append(DeadlineTimeoutEnvironmentEntry(PipelineKeys.DeadlineDeliveryTimeout, self.dialog.deliveryDeadlineTimeout, valueType=int))

        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.BaseScenesFolder, self.dialog.baseScenesFolderEdit, self, self.dialog.baseScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.InputScenesFolder, self.dialog.inputScenesFolderEdit, self, self.dialog.inputScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.CreatedInputScenesFolder, self.dialog.createdInputScenesFolderEdit, self, self.dialog.createdInputScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.RenderScenesFolder, self.dialog.renderScenesFolderEdit, self, self.dialog.renderScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.EnvironmentScenesFolder, self.dialog.environmentScenesEdit, self, self.dialog.environmentScenesButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.NukeScenesFolder, self.dialog.nukeScenesFolderEdit, self, self.dialog.nukeScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.BlenderCompositingScenesFolder, self.dialog.blenderCompositingScenesFolderEdit, self, self.dialog.blenderCompositingScenesFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.RenderingsFolder, self.dialog.renderingsFolderEdit, self, self.dialog.renderingsFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.PostFolder, self.dialog.postFolderEdit, self, self.dialog.postFolderButton))
        self.environmentEntries.append(ProjectSubFolderEnvironmentEntry(PipelineKeys.DeliveryFolder, self.dialog.deliveryFolderEdit, self, self.dialog.deliveryFolderButton))

        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.BaseSceneNaming, self.dialog.baseSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.SidNaming, self.dialog.sidNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.RenderSceneNaming, self.dialog.renderSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.InputSceneNaming, self.dialog.inputSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.CreatedInputSceneNaming, self.dialog.createdInputSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.NukeSceneNaming, self.dialog.nukeSceneNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.BlenderCompositingSceneNaming, self.dialog.blenderCompositingNamingEdit))
        self.environmentEntries.append(NamingEnvironmentEntry(PipelineKeys.EnvironmentSceneNaming, self.dialog.environmentSceneNamingEdit))

        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.SaveRenderScene, self.dialog.saveRenderSceneCheckBox, PipelineType.Blender))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.RenderInSceneCreationScript, self.dialog.renderInSceneCreationScriptCheckBox, PipelineType.Blender))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(PipelineKeys.ApplyCameraFraming, self.dialog.applyCameraFramingCheckBox, PipelineType.Blender))

        # Unreal Engine
        self.environmentEntries.append(ProjectFileEnvironmentEntry(UnrealEnginePipelineKeys.ProjectFilename, self.dialog.ueProjectFilenameEdit, self,
            self.dialog.ueProjectFilenameButton, fileFilter='UE Project (*.uproject)'))
        self.environmentEntries.append(NamingEnvironmentEntry(UnrealEnginePipelineKeys.MoviePipelineQueueSettings, self.dialog.ueMoviePipelineQueueSettings))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(UnrealEnginePipelineKeys.VSync, self.dialog.ueVSyncCheckBox))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(UnrealEnginePipelineKeys.KeepExtensionSettings, self.dialog.ueKeepExtensionSettingsCheckBox))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(UnrealEnginePipelineKeys.KeepFileNameFormat, self.dialog.ueKeepFileNameFormatCheckBox))
        self.environmentEntries.append(CheckBoxEnvironmentEntry(UnrealEnginePipelineKeys.OverrideWindowResolution, self.dialog.ueOverrideWindowResolutionCheckBox))
        self.environmentEntries.append(LineEditEnvironmentEntry(UnrealEnginePipelineKeys.WindowResolutionX, self.dialog.ueWindowResolutionX, valueType=int))
        self.environmentEntries.append(LineEditEnvironmentEntry(UnrealEnginePipelineKeys.WindowResolutionY, self.dialog.ueWindowResolutionY, valueType=int))

        self.dialog.ueOverrideWindowResolutionCheckBox.stateChanged.connect(lambda: self.dialog.ueWindowResolutionFrame.setEnabled(self.dialog.ueOverrideWindowResolutionCheckBox.isChecked()))

        self.perspectiveToNamingConventionEnvEntries: Dict[str,List[EnvironmentEntry]] = dict()

        self.dialog.perspectiveCodesEdit.editingFinished.connect(self.perspectiveCodesEditingFinished)

        self.fetchedPoolNames = False
        self.serviceRegistry.deadlineService.onConnected.once(lambda: threading_util.runInThread(self.fetchDeadlinePoolNames))
        threading_util.runInThread(self.fetchDeadlinePoolNames)
        
        self.refreshAvailablePipelineMenu()
        self.updateTabs()
        self.registerFilters()

        self.viewerRegistry.collectionViewer.refreshCollections()

        self.environmentViewer = EnvironmentViewer(self.dialog, self.environmentManager, self.dbManager)
        self.dialog.environmentViewerLayout.addWidget(self.environmentViewer.widget)
        self.environment = Environment()
        self.environmentViewer.setEnvironment(self.environment)
        self.environmentViewer.setKeyDisplayIgnoreFilter('^rp_.*')
        self.environmentViewer.allowSave = False

        self.rowSkipConditions: List[RowSkipConditionUIElement] = []
        self.dialog.addRowSkipConditionButton.clicked.connect(self.onAddRowSkipConditionClick)

        self.customSubmissionTaskViewer = CustomSubmissionTaskViewer(self.dialog, serviceRegistry, viewerRegistry)
        self.taskExecutionOrderView = TaskExecutionOrderView(self.customSubmissionTaskViewer, self.dialog)

        self.dialog.selectProductTableInExplorerButton.clicked.connect(self.onSelectProductTableInExplorerClick)
        self.dialog.refreshTableHeaderButton.clicked.connect(self.onRefreshTableHeaderClick)

    @property
    def baseProjectFolderPath(self):
        return self.baseProjectFolderElement.edit.text()

    def onSelectProductTableInExplorerClick(self):
        try:
            windows_nodes.selectInExplorer(self.productTableEnvEntry.getAbsoluteFilename())
        except:
            pass

    def onRefreshTableHeaderClick(self):
        self.onProductTableChanged(self.productTableEnvEntry.getAbsoluteFilename())

    def onAddRowSkipConditionClick(self):
        if not self.currentHeader:
            QtWidgets.QMessageBox.warning(self.dialog, "No Table Header", "Please specify a valid product table first.")
            return

        rowSkipCondition = RowSkipConditionUIElement(self.currentHeader)
        self.addRowSkipCondition(rowSkipCondition)

    def addRowSkipCondition(self, rowSkipCondition: RowSkipConditionUIElement):
        rowSkipCondition.deleteButton.clicked.connect(lambda: self.removeRowSkipCondition(rowSkipCondition))
        self.rowSkipConditions.append(rowSkipCondition)
        self.dialog.rowSkipConditionLayout.addLayout(rowSkipCondition)

    def removeRowSkipCondition(self, rowSkipCondition: RowSkipConditionUIElement):
        self.rowSkipConditions.remove(rowSkipCondition)
        
        for idx, child in enumerate(self.dialog.rowSkipConditionLayout.children()):
            if child == rowSkipCondition:
                self.dialog.rowSkipConditionLayout.takeAt(idx)
                qt_util.clearContainer(child)
                child.deleteLater()

    def loadRowSkipConditions(self, pipeline: RenderingPipeline):
        self.rowSkipConditions = []
        qt_util.clearContainer(self.dialog.rowSkipConditionLayout)
        skipConditions = pipeline.getCustomDataValue('rowSkipConditions')
        if skipConditions:
            header = pipeline.getCustomDataValue('header', [])
            for skipConditionDict in skipConditions:
                skipCondition = RowSkipConditionUIElement(header)
                skipCondition.setFromDict(skipConditionDict)
                self.addRowSkipCondition(skipCondition)

    def saveRowSkipConditions(self, pipeline: RenderingPipeline):
        rowSkipConditions = [condition.getAsDict() for condition in self.rowSkipConditions]
        pipeline.setCustomDataEntry('rowSkipConditions', rowSkipConditions)
        pipeline.setCustomDataEntry('header', self.currentHeader)

    def onPipelineClassRegistered(self):
        self.updatePipelineClassComboBox()
        self.refreshAvailablePipelineMenu()

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

                    if self.environment:
                        envEntry.loadValue(self.environment)

    def initIconMap(self):
        deadlineRepoFolder = self.serviceRegistry.deadlineService.info.deadlineRepositoryLocation
        self.iconMap = dict()

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins', 'Blender', 'Blender.ico')):
            self.iconMap[PipelineType.Blender.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins', 'Blender', 'Blender.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins','3dsmax', '3dsmax.ico')):
            self.iconMap[PipelineType.Max3ds.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins','3dsmax', '3dsmax.ico'))

        if os.path.exists(os.path.join(deadlineRepoFolder, 'plugins','UnrealEngine', 'UnrealEngine.ico')):
            self.iconMap[PipelineType.UnrealEngine.value] = QtGui.QIcon(os.path.join(deadlineRepoFolder, 'plugins','UnrealEngine', 'UnrealEngine.ico'))

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
                pipeline.activate()
                self.viewerRegistry.environmentManagerViewer.setCurrentEnvironment(pipeline.environment)
            self.pipelineSelectionMenu.setTitle(f'Selected RP: {selectedPipelineName}')

    def onPipelineSelected(self, pipelineName: str):
        self.selectPipelineFromName(pipelineName)

    def selectPipelineFromName(self, pipelineName: str):
        pipeline = self.renderingPipelineManager.getPipelineFromName(pipelineName)
        if pipeline:
            pipeline.activate()
            self.viewerRegistry.collectionViewer.showSingleCollection(pipeline.dbCollectionName)
            self.viewerRegistry.environmentManagerViewer.setCurrentEnvironment(pipeline.environment)
            self.viewerRegistry.documentSearchFilterViewer.viewItems(saveSearchHistoryEntry=False)
            self.pipelineSelectionMenu.setTitle(f'Selected RP: {pipeline.name}')
            self.appInfo.settings.setValue('SelectedRenderingPipeline', pipeline.name)

    def fetchDeadlinePoolNames(self):
        poolNames = getDeadlinePoolNames(quiet=True)
        qt_util.runInMainThread(self.onDeadlinePoolNamesFetched, poolNames)

    def onDeadlinePoolNamesFetched(self, poolNames: List[str]):
        if self.fetchedPoolNames:
            return

        if poolNames is None:
            poolNames = []

        if 'none' in poolNames:
            poolNames.remove('none')

        poolNames.insert(0, 'none')
            
        self.updateDeadlinePoolComboBox(self.dialog.deadlineInputScenePoolComboBox, poolNames, PipelineKeys.DeadlineInputScenePool)
        self.updateDeadlinePoolComboBox(self.dialog.deadlineRenderScenePoolComboBox, poolNames, PipelineKeys.DeadlineRenderScenePool)
        self.updateDeadlinePoolComboBox(self.dialog.deadlineRenderingPoolComboBox, poolNames, PipelineKeys.DeadlineRenderingPool)
        self.updateDeadlinePoolComboBox(self.dialog.deadlineNukePoolComboBox, poolNames, PipelineKeys.DeadlineNukePool)
        self.updateDeadlinePoolComboBox(self.dialog.deadlineBlenderCompositingPoolComboBox, poolNames, PipelineKeys.DeadlineBlenderCompositingPool)
        self.updateDeadlinePoolComboBox(self.dialog.deadlineDeliveryPoolComboBox, poolNames, PipelineKeys.DeadlineDeliveryPool)

        if poolNames:
            self.fetchedPoolNames = True

    def updateDeadlinePoolComboBox(self, comboBox: QtWidgets.QComboBox, poolNames: List[str], envKey: str):
        existingEnvEntry = None
        for envEntry in self.environmentEntries:
            if envEntry.envKey == envKey:
                existingEnvEntry = envEntry
                break

        if not existingEnvEntry:
            self.environmentEntries.append(DeadlinePoolComboBoxEnvironmentEntry(envKey, comboBox))

        if poolNames:
            existingItems = set(comboBox.itemText(i) for i in range(comboBox.count()))
            curText = comboBox.currentText()
            for name in poolNames:
                if not name in existingItems:
                    comboBox.addItem(name)

            if curText:
                comboBox.setCurrentText(curText)

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

        if not pipelineName:
            self.dialog.statusLabel.setText(f'Please specify a pipeline name.')
            return

        envId = EnvironmentManager.getIdFromEnvironmentName(pipelineName)

        if self.dialog.updateCollectionCheckBox.isChecked() and not self.dialog.headerConfirmationCheckBox.isChecked():
            self.dialog.statusLabel.setText(f'Please confirm the table extraction.')
            return

        notAllowedHeaderKeys = [Keys.preview]
        if any(key in self.currentHeader for key in notAllowedHeaderKeys):
            self.dialog.statusLabel.setText(f'The following table header keys are used internally by the pipeline and thus should not be present: {notAllowedHeaderKeys}')
            return

        baseProjectFolder = self.baseProjectFolderElement.edit.text()
        pipelineType = self.dialog.pipelineTypeComboBox.currentText()
        pipelineClassName = self.dialog.pipelineClassComboBox.currentText()
        productTable = self.productTableEnvEntry.getAbsoluteFilename()
        sheetName = self.dialog.productTableSheetNameComboBox.currentText()
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

        self.environment.setUID(envId)
        pipeline = self.renderingPipelineManager.constructPipeline(pipelineName, pipelineClassName)
        self.saveRowSkipConditions(pipeline)
        pipeline.rowSkipConditions = [condition.evaluateCondition for condition in self.rowSkipConditions]

        try:
            self.customSubmissionTaskViewer.save(self.environment)
        except Exception as e:
            self.dialog.statusLabel.setText(str(e))
            return

        self.environment.settings[PipelineKeys.OrderedSubmitterInfos] = self.taskExecutionOrderView.getSubmitterInfosAsDict()

        self.environment.settings[PipelineKeys.PipelineType] = pipelineType
        self.environment.settings[PipelineKeys.PipelineClass] = pipelineClassName
        self.environment.settings[PipelineKeys.ProductTableSheetName] = sheetName
        self.environment.settings[PipelineKeys.ReplaceGermanCharacters] = replaceGermanChars
        self.environment.settings[PipelineKeys.RenderingExtension] = renderingExtension
        self.environment.settings[PipelineKeys.PostOutputExtensions] = postOutputExtensionsStr
        self.environment.settings[PipelineKeys.PerspectiveCodes] = perspectiveCodesStr

        self.environment.settings[PipelineKeys.SceneExtension] = self.getSceneExtensionFromPipelineType(pipelineType)

        try:
            for envEntry in self.environmentEntries:
                if envEntry.isApplicable():
                    envEntry.verify()
                    envEntry.saveValue(self.environment)
        except Exception as e:
            self.dialog.statusLabel.setText(str(e))
            return

        if pipelineType == PipelineType.UnrealEngine.value:
            # Generate required python source code in project location
            evaluatedSettings = self.environment.getEvaluatedSettings()
            ueProjectFolder = os.path.dirname(evaluatedSettings[UnrealEnginePipelineKeys.ProjectFilename])
            ueCodeFilename = os.path.join(ueProjectFolder, 'Content', 'Python', 'md_pipeline_init_unreal.py')
            try:
                os.makedirs(os.path.dirname(ueCodeFilename), exist_ok=True)
                code = generateUnrealEngineMoviePipelineExecutorCode()
                with open(ueCodeFilename, mode='w+') as f:
                    f.write(code)
            except Exception as e:
                self.dialog.statusLabel.setText(f'Failed to add required code at project location: {ueCodeFilename}. Exception: {e}')
                return

        pipelineExists = self.renderingPipelineManager.getPipelineFromName(pipelineName) != None

        # Read the table:
        if self.dialog.updateCollectionCheckBox.isChecked():
            try:
                replaceExistingCollection = pipelineExists and self.dialog.replaceExistingCollectionCheckBox.isChecked()
                progressDialog = ProgressDialog()
                progressDialog.open()
                self.dialog.statusLabel.setText('')
                self.dialog.logTextEdit.clear()
                logHandler = lambda msg: self.dialog.logTextEdit.append(msg)
                pipeline.readProductTable(productTablePath=productTable, productTableSheetname=sheetName, environmentSettings=self.environment.getEvaluatedSettings(), 
                                        onProgressUpdate=progressDialog.updateProgress, replaceExistingCollection=replaceExistingCollection, logHandler=logHandler)
            except Exception as e:
                self.dialog.statusLabel.setText(f'Failed reading the product table {productTable} with exception: {str(e)}')
                return
            finally:
                progressDialog.close()

        self.renderingPipelineManager.addNewPipelineInstance(pipeline, replaceExisting=True)
        self.environmentManager.addEnvironment(self.environment, save=True, replaceExisting=False)

        self.viewerRegistry.environmentManagerViewer.refreshEnvironmentsComboBox()
        self.viewerRegistry.collectionViewer.refreshCollections()
        self.refreshAvailablePipelineMenu()

        if not pipelineExists:
            self.selectPipelineFromName(pipelineName)
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
            prevEnv = self.environment
            self.environment = Environment(EnvironmentManager.getIdFromEnvironmentName(pipelineName))
            if prevEnv:
                self.environment.settingsDict = prevEnv.settingsDict.copy()

            self.environmentViewer.setEnvironment(self.environment)
            self.dialog.createButton.setText(' Create')
            self.dialog.updateCollectionCheckBox.setText('Create Table')
            self.dialog.deleteButton.setVisible(False)
            self.dialog.replaceExistingCollectionCheckBox.setVisible(False)

    def refreshProductSheetNameComboBox(self):
        self.dialog.productTableSheetNameComboBox.clear()
        productTablePath = self.productTableEnvEntry.getAbsoluteFilename()

        if os.path.exists(productTablePath):
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
        productTablePath = self.productTableEnvEntry.getAbsoluteFilename()
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
        self.environment = self.environmentManager.getEnvironmentFromName(pipeline.environmentName)
        if not self.environment:
            self.environment = Environment(EnvironmentManager.getIdFromEnvironmentName(pipelineName))

        environmentSettings = self.environment.settings
        self.customSubmissionTaskViewer.load(self.environment)

        if pipeline:
            self.dialog.pipelineTypeComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineType, ''))
            self.dialog.pipelineClassComboBox.setCurrentText(environmentSettings.get(PipelineKeys.PipelineClass, ''))
            self.dialog.productTableSheetNameComboBox.setCurrentText(environmentSettings.get(PipelineKeys.ProductTableSheetName, ''))
            self.dialog.replaceGermanCharactersCheckBox.setChecked(environmentSettings.get(PipelineKeys.ReplaceGermanCharacters, True))
            self.dialog.perspectiveCodesEdit.setText(environmentSettings.get(PipelineKeys.PerspectiveCodes, ''))
            self.dialog.renderingExtensionComboBox.setCurrentText(environmentSettings.get(PipelineKeys.RenderingExtension, ''))
            self.dialog.postOutputExtensionsEdit.setText(environmentSettings.get(PipelineKeys.PostOutputExtensions, ''))

            self.dialog.headerConfirmationCheckBox.setChecked(True)
            
            self.refreshPerspectiveTabWidget()
            
            for envEntry in self.environmentEntries:
                if envEntry.isApplicable():
                    envEntry.loadValue(self.environment)

            self.loadRowSkipConditions(pipeline)

            submitterInfos = getOrderedSubmitterInfos(environmentSettings)
            self.taskExecutionOrderView.setSubmitterInfos(submitterInfos)

        self.environmentViewer.setEnvironment(self.environment)

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
        elif pipelineType == PipelineType.UnrealEngine:
            return ''

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

        pipelineType = PipelineType(text)
        cb: QtWidgets.QComboBox = self.dialog.renderingExtensionComboBox
        currentRenderingExt = cb.currentText()
        cb.clear()

        if pipelineType == PipelineType.UnrealEngine:
            # Unreal currently does not support tifs:
            renderingExtensions = ['exr', 'png', 'jpg']
        else:
            renderingExtensions = ['exr', 'png', 'tif', 'jpg']

        cb.addItems(renderingExtensions)
        if currentRenderingExt in renderingExtensions:
            cb.setCurrentText(currentRenderingExt)

        self.taskExecutionOrderView.updateSubmitters(pipelineType)

    def updateTabs(self):
        pipelineType = PipelineType(self.dialog.pipelineTypeComboBox.currentText())
        tabWidget: QtWidgets.QTabWidget = self.dialog.tabWidget

        if pipelineType == PipelineType.Max3ds:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.unrealEngineTab))
            tabWidget.addTab(self.dialog.max3dsTab, '3dsMax')

            if self.iconMap.get(PipelineType.Max3ds.value):
                tabWidget.setTabIcon(tabWidget.indexOf(self.dialog.max3dsTab), self.iconMap.get(PipelineType.Max3ds.value))
        elif pipelineType == PipelineType.Blender:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.max3dsTab))
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.unrealEngineTab))
            tabWidget.addTab(self.dialog.blenderTab, 'Blender')

            if self.iconMap.get(PipelineType.Blender.value):
                tabWidget.setTabIcon(tabWidget.indexOf(self.dialog.blenderTab), self.iconMap.get(PipelineType.Blender.value))
        elif pipelineType == PipelineType.UnrealEngine:
            tabWidget.removeTab(tabWidget.indexOf(self.dialog.max3dsTab))
            tabWidget.addTab(self.dialog.unrealEngineTab, 'UE')

            if self.iconMap.get(PipelineType.UnrealEngine.value):
                tabWidget.setTabIcon(tabWidget.indexOf(self.dialog.unrealEngineTab), self.iconMap.get(PipelineType.UnrealEngine.value))

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
        SourceCodeTemplateGeneration.generateBlenderSourceCodeTemplate(self.dialog.blenderCompositingSourceCodeTemplateEdit, SourceCodeTemplateSceneType.Compositing)
        SourceCodeTemplateGeneration.generateUnrealEngineSourceCodeTemplate(self.dialog.ueInputSceneSourceCodeTemplateEdit_2, SourceCodeTemplateSceneType.InputScene)
        SourceCodeTemplateGeneration.generateUnrealEngineSourceCodeTemplate(self.dialog.ueRenderSceneSourceCodeTemplateEdit, SourceCodeTemplateSceneType.RenderScene)

        self.dialog.pipelineNameComboBox.currentTextChanged.disconnect()
        self.refreshPipelineNameComboBox()
        self.dialog.pipelineNameComboBox.currentTextChanged.connect(self.onPipelineNameChanged)
        self.dialog.show()
        self.dialog.activateWindow()
        self.dialog.raise_()

    def hide(self):
        self.dialog.hide()