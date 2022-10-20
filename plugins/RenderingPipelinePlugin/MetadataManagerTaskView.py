import typing
import PySide2
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget
from MetadataManagerCore.Event import Event
from MetadataManagerCore.actions.Action import Action
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.environment.Environment import Environment
from RenderingPipelinePlugin.RenderingPipeline import RenderingPipeline
from RenderingPipelinePlugin.submitters.MetadataManagerSubmissionTaskSettings import MetadataManagerSubmissionTaskSettings
import asset_manager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from RenderingPipelinePlugin.RenderingPipelineViewer import RenderingPipelineViewer

class MetadataManagerTaskView(object):
    def __init__(self, actionManager: ActionManager, taskIdx: int, renderingPipelineViewer: "RenderingPipelineViewer") -> None:
        super().__init__()
        
        self.actionManager = actionManager
        self.renderingPipelineViewer = renderingPipelineViewer

        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "assets/customTask.ui")
        self.widget = asset_manager.loadUIFileAbsolutePath(uiFilePath)

        self.widget.destroyed.connect(self.onDestroyed)

        self.formLayout: QFormLayout = self.widget.formLayout
        self.actionsComboBox: QComboBox = self.widget.actionsComboBox

        self.actionIdSet = set()
        
        for a in self.actionManager.actions:
            self.addAction(a)

        self.actionManager.registerActionEvent.subscribe(self.addAction)

        self.widget.addOutputFilenameButton.clicked.connect(self.addOutputFilenameRow)

        self.widget.deleteButton.clicked.connect(self.onDeleteClick)

        self.labelToFilenameEditDict: typing.Dict[QLineEdit, QLineEdit] = dict()

        self.taskIdx = taskIdx

        self.onBeforeDelete = Event()
        self.onNameChanged = Event()

        self.widget.nameEdit.textChanged.connect(lambda newName: self.onNameChanged(newName))

    def onDestroyed(self):
        self.actionManager.registerActionEvent.unsubscribe(self.addAction)

    @property
    def currentPipeline(self) -> RenderingPipeline:
        return self.renderingPipelineViewer.loadedPipeline

    def addAction(self, action: Action):
        if action.id in self.actionIdSet:
            return

        collectionActionIds = []

        if self.currentPipeline:
            collectionActionIds = self.actionManager.getCollectionActionIds(self.currentPipeline.dbCollectionName)

        if action.category == 'Rendering Pipeline' and not action.id in collectionActionIds:
            return

        self.actionIdSet.add(action.id)
        self.actionsComboBox.addItem(action.displayName, action.id)

    @property
    def name(self):
        return self.widget.nameEdit.text()

    def onDeleteClick(self):
        if QMessageBox.question(self.widget, "Confirmation", f"Are you sure you want to delete the task {self.taskIdx}?") == QMessageBox.Yes:
            self.onBeforeDelete()
            
            self.widget.deleteLater()

    def addOutputFilenameRow(self, labelText: str = '', value: str = ''):
        layout = QHBoxLayout()
        delButton = QPushButton()
        delButton.setText("")
        delButton.setIcon(QIcon(':/icons/delete.png'))
        filenameEdit = QLineEdit()
        filenameEdit.setText(value)
        layout.addWidget(filenameEdit)
        layout.addWidget(delButton)
        labelEdit = QLineEdit()
        labelEdit.setText(labelText)
        self.formLayout.addRow(labelEdit, layout)

        def onDelete():
            if QMessageBox.question(self.widget, "Confirmation", f"Are you sure you want to delete the entry {labelEdit.text()}?") == QMessageBox.Yes:
                del self.labelToFilenameEditDict[labelEdit]
                layout.deleteLater()
                labelEdit.deleteLater()

        delButton.clicked.connect(onDelete)

        self.labelToFilenameEditDict[labelEdit] = filenameEdit

    def getSettings(self) -> MetadataManagerSubmissionTaskSettings:
        outputFilenames = set()
        outputFilenamesDict = dict()

        for labelEdit, filenameEdit in self.labelToFilenameEditDict.items():
            if labelEdit.text().replace(' ', '') == '':
                raise RuntimeError(f'Output filename of task {self.taskIdx} is empty.')

            if labelEdit.text() in outputFilenames:
                raise RuntimeError(f'Duplicate output filename {labelEdit.text()} in task {self.taskIdx}')

            outputFilenames.add(labelEdit.text())
            outputFilenamesDict[labelEdit.text()] = filenameEdit.text()

        taskSettings = MetadataManagerSubmissionTaskSettings({})
        taskSettings.actionId = self.actionsComboBox.currentData()
        taskSettings.name = self.widget.nameEdit.text()
        taskSettings.outputFilenames = outputFilenamesDict
        taskSettings.taskType = 'RenderingPipelineDocumentAction'

        return taskSettings

    def save(self, infoDict: dict):
        if not self.actionManager.getActionById(self.actionsComboBox.currentData()):
            raise RuntimeError(f'Invalid action selection in task {self.taskIdx}')

        if self.widget.nameEdit.text().replace(' ', '') == '':
            raise RuntimeError(f'Please specify a batch name for task {self.taskIdx}')

        d = self.getSettings().dataDict
        for key, value in d.items():
            infoDict[key] = value

    def load(self, infoDict: dict):
        settings = MetadataManagerSubmissionTaskSettings(infoDict)
        for i in range(self.actionsComboBox.count()):
            if self.actionsComboBox.itemData(i) == settings.actionId:
                self.actionsComboBox.setCurrentIndex(i)
                break
            
        self.widget.nameEdit.setText(settings.name)

        for key, value in settings.outputFilenamesDict.items():
            self.addOutputFilenameRow(key, value)

        return True