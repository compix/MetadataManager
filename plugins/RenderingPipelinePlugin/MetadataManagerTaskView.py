import typing
import PySide2
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QWidget
from MetadataManagerCore.Event import Event
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.environment.Environment import Environment
from RenderingPipelinePlugin.submitters.MetadataManagerSubmissionTaskSettings import MetadataManagerSubmissionTaskSettings
import asset_manager

class MetadataManagerTaskView(object):
    def __init__(self, actionManager: ActionManager, taskIdx: int) -> None:
        super().__init__()
        
        self.actionManager = actionManager

        uiFilePath = asset_manager.getPluginUIFilePath("RenderingPipelinePlugin", "assets/customTask.ui")
        self.widget = asset_manager.loadUIFileAbsolutePath(uiFilePath)

        self.formLayout: QFormLayout = self.widget.formLayout
        self.actionsComboBox: QComboBox = self.widget.actionsComboBox

        ignoredCategories = ["Rendering Pipeline"]

        for a in self.actionManager.actions:
            if not a.category in ignoredCategories:
                self.actionsComboBox.addItem(a.displayName, a.id)

        self.widget.addOutputFilenameButton.clicked.connect(self.addOutputFilenameRow)

        self.widget.deleteButton.clicked.connect(self.onDeleteClick)

        self.labelToFilenameEditDict: typing.Dict[QLineEdit, QLineEdit] = dict()

        self.taskIdx = taskIdx

        self.onBeforeDelete = Event()
        self.onNameChanged = Event()

        self.widget.nameEdit.textChanged.connect(lambda newName: self.onNameChanged(newName))

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

        return MetadataManagerSubmissionTaskSettings(self.actionsComboBox.currentData(), self.widget.nameEdit.text(), outputFilenamesDict)

    def save(self, infoDict: dict):
        if not self.actionManager.getActionById(self.actionsComboBox.currentData()):
            raise RuntimeError(f'Invalid action selection in task {self.taskIdx}')

        if self.widget.nameEdit.text().replace(' ', '') == '':
            raise RuntimeError(f'Please specify a batch name for task {self.taskIdx}')

        d = self.getSettings().toDict()
        for key, value in d.items():
            infoDict[key] = value

    def load(self, infoDict: dict):
        settings = MetadataManagerSubmissionTaskSettings.fromDict(infoDict)
        for i in range(self.actionsComboBox.count()):
            if self.actionsComboBox.itemData(i) == settings.actionId:
                self.actionsComboBox.setCurrentIndex(i)
                break
            
        self.widget.nameEdit.setText(settings.name)

        for key, value in settings.outputFilenamesDict.items():
            self.addOutputFilenameRow(key, value)

        return True