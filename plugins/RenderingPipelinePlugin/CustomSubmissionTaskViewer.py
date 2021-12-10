import typing
from PySide2.QtWidgets import QDialog, QVBoxLayout
from MetadataManagerCore.Event import Event
from MetadataManagerCore.environment.Environment import Environment
from RenderingPipelinePlugin import PipelineKeys

from RenderingPipelinePlugin.MetadataManagerTaskView import MetadataManagerTaskView
from ServiceRegistry import ServiceRegistry
from viewers.ViewerRegistry import ViewerRegistry

class CustomSubmissionTaskViewer(object):
    def __init__(self, renderingPipelineDialog: QDialog, serviceRegistry: ServiceRegistry, viewerRegistry: ViewerRegistry) -> None:
        super().__init__()

        self.serviceRegistry = serviceRegistry
        self.viewerRegistry = viewerRegistry
        self.renderingPipelineDialog = renderingPipelineDialog
        self.onSubmissionTaskViewDeleted = Event()
        self.onSubmissionTaskViewAdded = Event()
        self.onSubmissionTaskViewNameChanged = Event()

        renderingPipelineDialog.newCustomTaskButton.clicked.connect(self.onNewCustomTaskClick)

        self.taskViews: typing.List[MetadataManagerTaskView] = []

        self.tasksLayout: QVBoxLayout = self.renderingPipelineDialog.customTasksFrame.layout()

    def getViewByName(self, name: str) -> MetadataManagerTaskView:
        for v in self.taskViews:
            if v.name == name:
                return v

        return None
        
    def onNewCustomTaskClick(self):
        self.addCustomTask()

    def addCustomTask(self, customTaskDict: dict=None):
        taskView = MetadataManagerTaskView(self.serviceRegistry.actionManager, len(self.taskViews))
        taskView.onBeforeDelete.subscribe(lambda: self.removeTask(taskView))
        self.taskViews.append(taskView)

        self.tasksLayout.addWidget(taskView.widget)

        if customTaskDict:
            taskView.load(customTaskDict)
        
        taskView.onNameChanged.subscribe(lambda newName: self.onSubmissionTaskViewNameChanged(taskView))
        self.onSubmissionTaskViewAdded(taskView)
        return taskView
    
    def removeTask(self, taskView: MetadataManagerTaskView):
        self.taskViews.remove(taskView)
        self.onSubmissionTaskViewDeleted(taskView)

    def save(self, env: Environment):
        customTasks = []
        names = set()
        for taskView in self.taskViews:
            taskDict = dict()
            taskView.save(taskDict)
            customTasks.append(taskDict)

            name = taskDict['name']
            if name in names:
                raise RuntimeError(f'Duplicate task name: {name} - Please rename one of the tasks.')
            
            names.add(name)

        env.settings[PipelineKeys.CustomTasks] = customTasks

    def load(self, env: Environment):
        for taskView in self.taskViews:
            self.onSubmissionTaskViewDeleted(taskView)
            taskView.widget.deleteLater()
        
        self.taskViews = []
        customTasks = env.settings.get(PipelineKeys.CustomTasks)
        if customTasks:
            for customTask in customTasks:
                self.addCustomTask(customTask)