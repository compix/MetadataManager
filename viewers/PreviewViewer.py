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

    def idxToFrameString(self, idx, maxDigits):
        s = str(idx)

        if len(s) > maxDigits:
            raise f"Invalid input: The index {idx} exceeds the max digit count {maxDigits}"

        for _ in range(len(s), maxDigits):
            s = "0" + s
        
        return s

    def displayPreview(self, path, resetZoom=True):
        scene = QtWidgets.QGraphicsScene()
        pixmap = QtGui.QPixmap(path)
        scene.addPixmap(pixmap)
        #self.preview.setScene(scene)
        self.preview.setPhoto(pixmap, resetZoom=resetZoom)
        #self.preview.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)

    def showPreview(self, path):
        if path == None or not os.path.exists(path):
            path = asset_manager.getImagePath('missing_rendering.jpg')

        self.curFrameIdx = 0
        self.frames = []

        # Check for animation frame pattern:
        idxStart = path.find("#")
        idxEnd = path.rfind("#")
        
        if idxStart >= 0:
            maxDigits = (idxEnd + 1) - idxStart

            for i in range(0,10**maxDigits):
                frameStr = self.idxToFrameString(i, maxDigits)
                framePath = frameStr.join([path[:idxStart],path[idxEnd+1:]])

                if os.path.exists(framePath):
                    self.frames.append(framePath)
                elif i > 0: # Support frames starting at 1
                    break
            
            if self.curFrameIdx < len(self.frames):
                self.displayPreview(self.frames[self.curFrameIdx])

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
