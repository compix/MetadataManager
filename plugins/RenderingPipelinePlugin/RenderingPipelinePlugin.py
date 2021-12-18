from ApplicationMode import ApplicationMode
from PySide2 import QtWidgets
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager
from RenderingPipelinePlugin.RenderingPipelineViewer import RenderingPipelineViewer
from plugin.Plugin import Plugin
import RenderingPipelinePlugin.visual_scripting_nodes.rendering_pipeline_nodes as rp_nodes

class RenderingPipelinePlugin(Plugin):
    def __init__(self) -> None:
        super().__init__()

    def init(self):
        self.renderingPipelineManager = RenderingPipelineManager(self.serviceRegistry, self.viewerRegistry, self.appInfo)
        rp_nodes.RENDERING_PIPELINE_MANAGER = self.renderingPipelineManager

        if self.appInfo.mode == ApplicationMode.GUI:
            menuBar = self.viewerRegistry.mainWindowManager.menuBar
            pipelineMenu = QtWidgets.QMenu("Rendering Pipeline")

            self.createAction = QtWidgets.QAction("Manage Pipeline")
            self.createAction.triggered.connect(self.onCreate)
            pipelineMenu.addAction(self.createAction)

            menuBar.addMenu(pipelineMenu)

            self.renderingPipelineViewer = RenderingPipelineViewer(self.viewerRegistry.mainWindowManager.window, self.renderingPipelineManager, self.serviceRegistry, self.viewerRegistry, self.appInfo)

    def onCreate(self):
        if self.appInfo.mode == ApplicationMode.GUI:
            self.renderingPipelineViewer.show()