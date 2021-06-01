from MetadataManagerCore.animation import anim_util
from MetadataManagerCore.mongodb_manager import MongoDBManager
from PySide2 import QtWidgets, QtCore, QtUiTools, QtGui
from MetadataManagerCore import Keys
from qt_extensions.DockWidget import DockWidget
import os
import asset_manager
from qt_extensions.PhotoViewer import PhotoViewer
from PySide2.QtCore import QRunnable
import time

def clearContainer(container):
    for i in reversed(range(container.count())): 
        container.itemAt(i).widget().setParent(None)

class PreviewViewer(DockWidget):
    def __init__(self, parentWindow):
        super().__init__("Preview", parentWindow, asset_manager.getUIFilePath("previewViewer.ui"))

        self.preview = PhotoViewer(self.widget)
        self.preview.toggleDragMode()
        self.widget.previewFrame.layout().addWidget(self.preview)
        self.widget.playButton.clicked.connect(self.onPlay)
        self.widget.pauseButton.clicked.connect(self.onPause)
        self.widget.nextFrameButton.clicked.connect(self.onNextFrame)
        self.widget.previousFrameButton.clicked.connect(self.onPreviousFrame)
        self.widget.selectBackgroundColorButton.clicked.connect(self.selectBackgroundColor)

        self.curFrameIdx = 0
        self.frames = []
        self.pixmapCacheDict = dict()

        self.widget.animationSpeedSlider.valueChanged.connect(self.onAnimationSpeedSliderChanged)

        self.animationTimer = QtCore.QTimer()
        self.animationTimer.setInterval(self.widget.animationSpeedSlider.maximum() - self.widget.animationSpeedSlider.value() + 1)
        self.animationTimer.timeout.connect(self.onUpdateAnimation)

    def onAnimationSpeedSliderChanged(self, value):
        self.animationTimer.setInterval(self.widget.animationSpeedSlider.maximum() - value + 1)

    def onPlay(self):
        self.animationTimer.start()

    def onPause(self):
        self.animationTimer.stop()

    def onNextFrame(self):
        self.showNextFrame()

    def onPreviousFrame(self):
        self.showPreviousFrame()

    def displayPreview(self, path, resetZoom=True):
        validPath = True
        if not os.path.exists(path):
            path = asset_manager.getImagePath('missing_rendering.jpg')
            validPath = False

        if path in self.pixmapCacheDict:
            self.preview.setPhoto(self.pixmapCacheDict[path], resetZoom=resetZoom)
            return True

        scene = QtWidgets.QGraphicsScene()
        pixmap = QtGui.QPixmap(path)
        scene.addPixmap(pixmap)
        self.preview.setPhoto(pixmap, resetZoom=resetZoom)
        self.pixmapCacheDict[path] = pixmap

        return validPath

    def showPreview(self, path):
        self.pixmapCacheDict = dict()

        self.animationTimer.stop()
        if path == None:
            self.displayPreview('')
            return

        if '#' in path:
            self.curFrameIdx = 0
            self.frames = anim_util.extractExistingFrameFilenames(path)

            if len(self.frames) > 0:
                if self.displayPreview(self.frames[self.curFrameIdx]):
                    self.animationTimer.start()
        else:
            self.displayPreview(path)

    def onUpdateAnimation(self):
        self.showNextFrame()

    def showNextFrame(self):
        if self.curFrameIdx < len(self.frames):
            self.curFrameIdx = (self.curFrameIdx + 1) % len(self.frames)
            self.displayPreview(self.frames[self.curFrameIdx], resetZoom=False)

    def showPreviousFrame(self):
        if self.curFrameIdx < len(self.frames):
            self.curFrameIdx = (self.curFrameIdx - 1 + len(self.frames)) % len(self.frames)
            self.displayPreview(self.frames[self.curFrameIdx], resetZoom=False)

    def clearPreview(self):
        self.animationTimer.stop()
        self.frames = []
        self.preview.setPhoto(None)

    def selectBackgroundColor(self):
        self.backgroundColor = QtWidgets.QColorDialog.getColor()
        self.preview.setBackgroundBrush(self.backgroundColor)
