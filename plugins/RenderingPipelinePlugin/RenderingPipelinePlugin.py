from ApplicationMode import ApplicationMode
from PySide2 import QtWidgets
from RenderingPipelinePlugin.RenderingPipelineManager import RenderingPipelineManager
from RenderingPipelinePlugin.RenderingPipelineViewer import RenderingPipelineViewer
from plugin.Plugin import Plugin

class RenderingPipelinePlugin(Plugin):
    def __init__(self) -> None:
        super().__init__()

    def init(self):
        self.renderingPipelineManager = RenderingPipelineManager(self.serviceRegistry.environmentManager, self.serviceRegistry.dbManager)

        if self.appInfo.mode == ApplicationMode.GUI:
            menuBar = self.viewerRegistry.mainWindowManager.menuBar
            pipelineMenu = QtWidgets.QMenu("Rendering Pipeline")

            self.createAction = QtWidgets.QAction("Create")
            self.createAction.triggered.connect(self.onCreate)
            pipelineMenu.addAction(self.createAction)

            menuBar.addMenu(pipelineMenu)

            self.renderingPipelineViewer = RenderingPipelineViewer(self.viewerRegistry.mainWindowManager.window, self.renderingPipelineManager, self.serviceRegistry, self.viewerRegistry)

    def onCreate(self):
        if self.appInfo.mode == ApplicationMode.GUI:
            self.renderingPipelineViewer.show()