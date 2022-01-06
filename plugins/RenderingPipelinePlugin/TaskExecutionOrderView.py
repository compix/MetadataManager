import typing
from PySide2 import QtWidgets
from PySide2.QtWidgets import QDialog
from RenderingPipelinePlugin.PipelineType import PipelineType
from RenderingPipelinePlugin.CustomSubmissionTaskViewer import CustomSubmissionTaskViewer
from RenderingPipelinePlugin.MetadataManagerTaskView import MetadataManagerTaskView
from RenderingPipelinePlugin.submitters.BlenderCompositingSubmitter import BlenderCompositingSubmitter
from RenderingPipelinePlugin.submitters.DeliveryCopySubmitter import DeliveryCopySubmitter
from RenderingPipelinePlugin.submitters.Max3dsSubmitter import Max3dsInputSceneCreationSubmitter, Max3dsRenderSceneCreationSubmitter, Max3dsRenderingSubmitter
from RenderingPipelinePlugin.submitters.MetadataManagerTaskSubmitter import MetadataManagerTaskSubmitter
from RenderingPipelinePlugin.submitters.UnrealEngineSubmitter import UnrealEngineInputSceneCreationSubmitter, UnrealEngineRenderSceneCreationSubmitter, UnrealEngineRenderingSubmitter
from RenderingPipelinePlugin.submitters.BlenderSubmitter import BlenderInputSceneCreationSubmitter, BlenderRenderSceneCreationSubmitter, BlenderRenderingSubmitter
from RenderingPipelinePlugin.submitters.NukeSubmitter import NukeSubmitter
from RenderingPipelinePlugin.submitters.SubmitterInfo import SubmitterInfo, getPipelineSubmitterInfos, getPostSubmitterInfos

from qt_extensions import qt_util

class TaskExecutionOrderView(object):
    def __init__(self, customSubmissionTaskViewer: CustomSubmissionTaskViewer, mainDialog: QDialog) -> None:
        super().__init__()
        
        self.customSubmissionTaskViewer = customSubmissionTaskViewer
        self.mainDialog = mainDialog
        self.submitterInfos: typing.List[SubmitterInfo] = []
        self.curPipelineType: PipelineType = None

        self.customSubmissionTaskViewer.onSubmissionTaskViewDeleted.subscribe(self.onSubmissionTaskViewDeleted)
        self.customSubmissionTaskViewer.onSubmissionTaskViewAdded.subscribe(self.onSubmissionTaskViewAdded)
        self.customSubmissionTaskViewer.onSubmissionTaskViewNameChanged.subscribe(self.onSubmissionTaskViewNameChanged)
        self.updateSubmitters(PipelineType.Max3ds)
        self.mainDialog.taskExecutionOrderMoveUpButton.clicked.connect(self.onTaskExecutionOrderMoveUpClick)
        self.mainDialog.taskExecutionOrderMoveDownButton.clicked.connect(self.onTaskExecutionOrderMoveDownClick)

    def getSubmitterInfosAsDict(self) -> typing.List[dict]:
        return [i.toDict() for i in self.submitterInfos]

    def setSubmitterInfos(self, submitterInfos: typing.List[SubmitterInfo]):
        self.submitterInfos = submitterInfos
        self.updateTaskExecutionOrderLayout()

    def onTaskExecutionOrderMoveDownClick(self):
        if self.selectedTaskOrderExecutionButton:
            submitterInfo = self.selectedTaskOrderExecutionButton.submitterInfo
            idx = self.submitterInfos.index(submitterInfo)
            newIdx = (idx + 1) % len(self.submitterInfos)
            nextSubmitter = self.submitterInfos[newIdx]
            if submitterInfo == nextSubmitter:
                return

            self.submitterInfos.pop(idx)
            layout: QtWidgets.QVBoxLayout = self.mainDialog.taskExecutionOrderLayout
            item = layout.takeAt(idx)
            newIdx = self.submitterInfos.index(nextSubmitter)
            newIdx = newIdx if newIdx == 0 and idx != 0 else newIdx + 1
            self.submitterInfos.insert(newIdx, submitterInfo)
            layout.insertItem(newIdx, item)

    def onTaskExecutionOrderMoveUpClick(self):
        if self.selectedTaskOrderExecutionButton:
            submitterInfo = self.selectedTaskOrderExecutionButton.submitterInfo
            idx = self.submitterInfos.index(submitterInfo)
            newIdx = (idx - 1 + len(self.submitterInfos)) % len(self.submitterInfos)
            nextSubmitter = self.submitterInfos[newIdx]
            if submitterInfo == nextSubmitter:
                return

            self.submitterInfos.pop(idx)
            layout: QtWidgets.QVBoxLayout = self.mainDialog.taskExecutionOrderLayout
            item = layout.takeAt(idx)
            newIdx = self.submitterInfos.index(nextSubmitter)
            if newIdx == len(self.submitterInfos) - 1 and idx != len(self.submitterInfos):
                newIdx += 1

            self.submitterInfos.insert(newIdx, submitterInfo)
            layout.insertItem(newIdx, item)
    
    def updateTaskExecutionOrderLayout(self):
        layout: QtWidgets.QVBoxLayout = self.mainDialog.taskExecutionOrderLayout
        qt_util.clearContainer(layout)
        self.taskExecutionOrderButtons = []
        self.selectedTaskOrderExecutionButton = None

        self.taskExecutionOrderButtons = []
        for submitterInfo in self.submitterInfos:
            taskView = self.customSubmissionTaskViewer.getViewByName(submitterInfo.name)
            self.addTaskExecutionOrderEntry(submitterInfo, taskView)

    def addTaskExecutionOrderEntry(self, submitterInfo: SubmitterInfo, taskView: MetadataManagerTaskView=None):
        if not submitterInfo in self.submitterInfos:
            self.submitterInfos.append(submitterInfo)

        layout: QtWidgets.QVBoxLayout = self.mainDialog.taskExecutionOrderLayout
        btn = QtWidgets.QPushButton(submitterInfo.name)
        btn.submitterInfo = submitterInfo
        btn.taskView = taskView
        submitterInfo.taskView = taskView
        self.taskExecutionOrderButtons.append(btn)
        self.setupTaskExecutionOrderButton(btn)
        layout.addWidget(btn)

        return btn

    def setupTaskExecutionOrderButton(self, btn: QtWidgets.QPushButton):
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.onTaskExecutionOrderButtonClicked(btn, self.taskExecutionOrderButtons))
    
    def onTaskExecutionOrderButtonClicked(self, button: QtWidgets.QPushButton, buttons: typing.List[QtWidgets.QPushButton]):
        self.selectedTaskOrderExecutionButton = button
        for btn in buttons:
            if btn != button:
                btn.setChecked(False)

    def onSubmissionTaskViewAdded(self, taskView: MetadataManagerTaskView):
        self.addTaskExecutionOrderEntry(SubmitterInfo(taskView.name, MetadataManagerTaskSubmitter), taskView)

    def onSubmissionTaskViewNameChanged(self, taskView: MetadataManagerTaskView):
        for btn in self.taskExecutionOrderButtons:
            if btn.taskView == taskView:
                btn.setText(taskView.name)
                btn.submitterInfo.name = taskView.name

    def onSubmissionTaskViewDeleted(self, taskView: MetadataManagerTaskView):
        idx = None
        for i, info in enumerate(self.submitterInfos):
            if info.taskView == taskView:
                idx = i
                break
        
        if idx == None:
            return

        self.submitterInfos.pop(idx)
        layout: QtWidgets.QVBoxLayout = self.mainDialog.taskExecutionOrderLayout
        item = layout.takeAt(idx)
        self.taskExecutionOrderButtons.remove(item.widget())
        item.widget().deleteLater()

    def updateSubmitters(self, pipelineType: PipelineType):
        if not self.curPipelineType is None:
            for n in getPipelineSubmitterInfos(self.curPipelineType):
                self.submitterInfos.remove(n)

            self.curPipelineType = pipelineType
        else:
            self.submitterInfos = getPostSubmitterInfos()

        newInfos = getPipelineSubmitterInfos(pipelineType)
        self.submitterInfos = newInfos + self.submitterInfos
        self.updateTaskExecutionOrderLayout()