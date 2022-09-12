from MetadataManagerCore.task_processor.TaskPicker import TaskPicker
from MetadataManagerCore.actions.ActionManager import ActionManager
from MetadataManagerCore.filtering.DocumentFilterManager import DocumentFilterManager
from RenderingPipelinePlugin.tasks.PipelineDocumentActionTask import PipelineDocumentActionTask
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager

class PipelineTaskPicker(TaskPicker):
    """
    Handles Action and DocumentAction task types.
    """
    def __init__(self, actionManager: ActionManager, pipelineManager: RenderingPipelineManager):
        super().__init__()

        self.actionManager = actionManager
        self.pipelineManager = pipelineManager

    def pickTask(self, taskType: str):
        """
        Returns an instance of a Task for the given taskType.
        """
        if taskType == 'RenderingPipelineDocumentAction':
            return PipelineDocumentActionTask(self.actionManager, self.pipelineManager)

        return None