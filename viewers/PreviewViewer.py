from MetadataManagerCore.mongodb_manager import MongoDBManager
from PySide2 import QtWidgets, QtCore, QtUiTools, QtGui
from MetadataManagerCore import Keys
from qt_extensions.DockWidget import DockWidget
import os
from assets import asset_manager
from qt_extensions.PhotoViewer import PhotoViewer

class PreviewViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Preview Viewer", parentWindow, asset_manager.getUIFilePath("previewViewer.ui"))

        self.preview = PhotoViewer(self.widget)
        self.preview.toggleDragMode()
        self.widget.previewFrame.layout().addWidget(self.preview)

    def showPreview(self, path):
        if path == None:
            self.clearPreview()
            return

        scene = QtWidgets.QGraphicsScene()
        pixmap = QtGui.QPixmap(path)
        scene.addPixmap(pixmap)
        #self.preview.setScene(scene)
        self.preview.setPhoto(pixmap)
        #self.preview.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def clearPreview(self):
        self.preview.setPhoto(None)