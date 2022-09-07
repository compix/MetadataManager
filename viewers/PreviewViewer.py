import typing
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
        self.previewFilenames: typing.List[str] = []
        self.curPreviewFilenameIdx = 0
        self.shownImageFilename: str = None
        self.preview.toggleDragMode()
        self.isPlaying = True
        self.autoLoadBigFiles = True
        self.playIcon = QtGui.QIcon(':/icons/play_icon.png')
        self.pauseIcon = QtGui.QIcon(':/icons/pause_icon.png')
        self.widget.previewFrame.layout().addWidget(self.preview)

        self.loadBigFileButton = QtWidgets.QPushButton('Load')
        self.loadBigFileButton.setVisible(False)
        self.loadBigFileButton.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.loadBigFileButton.clicked.connect(lambda: self.displayPreview(self.shownImageFilename, force=True))
        self.widget.previewFrame.layout().addWidget(self.loadBigFileButton)

        self.widget.playToggleButton.clicked.connect(self.onTogglePlay)
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

        self.widget.nextPreviewButton.hide()
        self.widget.prevPreviewButton.hide()
        self.widget.nextPreviewButton.clicked.connect(self.onNextPreviewClick)
        self.widget.prevPreviewButton.clicked.connect(self.onPrevPreviewClick)

    def onNextPreviewClick(self):
        if self.previewFilenames and len(self.previewFilenames) > 0:
            prevIdx = self.curPreviewFilenameIdx
            self.curPreviewFilenameIdx = (self.curPreviewFilenameIdx + 1) % len(self.previewFilenames)
            if prevIdx != self.curPreviewFilenameIdx:
                self.showPreview(self.previewFilenames[self.curPreviewFilenameIdx], autoLoadBigFiles=self.autoLoadBigFiles)

    def onPrevPreviewClick(self):
        if self.previewFilenames and len(self.previewFilenames) > 0:
            prevIdx = self.curPreviewFilenameIdx
            self.curPreviewFilenameIdx = (self.curPreviewFilenameIdx - 1 + len(self.previewFilenames)) % len(self.previewFilenames)
            if prevIdx != self.curPreviewFilenameIdx:
                self.showPreview(self.previewFilenames[self.curPreviewFilenameIdx], autoLoadBigFiles=self.autoLoadBigFiles)

    def onAnimationSpeedSliderChanged(self, value):
        self.animationTimer.setInterval(self.widget.animationSpeedSlider.maximum() - value + 1)

    def onTogglePlay(self):
        self.isPlaying = not self.isPlaying
        if self.isPlaying:
            self.widget.playToggleButton.setIcon(self.pauseIcon)
            self.animationTimer.start()
        else:
            self.widget.playToggleButton.setIcon(self.playIcon)
            self.animationTimer.stop()

    def onNextFrame(self):
        self.showNextFrame()

    def onPreviousFrame(self):
        self.showPreviousFrame()

    def displayPreview(self, path: str, resetZoom=True, force=False):
        self.shownImageFilename = path
        validPath = True
        if not os.path.exists(path):
            path = asset_manager.getImagePath('missing_rendering.jpg')
            validPath = False

        self.loadBigFileButton.setVisible(False)
        self.preview.setVisible(True)

        if path in self.pixmapCacheDict:
            self.preview.setPhoto(self.pixmapCacheDict[path], resetZoom=resetZoom)
            return True

        if not force and not self.autoLoadBigFiles:
            stats = os.stat(path)
            fileSize = float(stats.st_size)
            fileSizeInMb = fileSize / 1024.0 / 1024.0

            if fileSizeInMb > 2.5:
                self.loadBigFileButton.setVisible(True)
                self.loadBigFileButton.setText(f'Load ({int(round(fileSizeInMb*10))/10.0} MB)')
                self.preview.setVisible(False)
                return False

        scene = QtWidgets.QGraphicsScene()
        pixmap = QtGui.QPixmap(path)
        scene.addPixmap(pixmap)
        self.preview.setPhoto(pixmap, resetZoom=resetZoom)
        self.pixmapCacheDict[path] = pixmap

        return validPath

    def showPreview(self, path: str, autoLoadBigFiles=True):
        self.autoLoadBigFiles = autoLoadBigFiles
        self.pixmapCacheDict = dict()

        self.animationTimer.stop()
        if path == None:
            self.displayPreview('')
            return

        if '#' in path:
            self.curFrameIdx = 0
            self.frames = anim_util.extractExistingFrameFilenames(path)

            if len(self.frames) > 0:
                if self.displayPreview(self.frames[self.curFrameIdx]) and self.isPlaying:
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

    def showMultiplePreviews(self, previewFilenames: typing.List[str], autoLoadBigFiles=True):
        self.autoLoadBigFiles = autoLoadBigFiles
        self.previewFilenames = previewFilenames
        self.curPreviewFilenameIdx = 0

        if not previewFilenames or len(self.previewFilenames) == 0:
            self.showPreview(None, autoLoadBigFiles=self.autoLoadBigFiles)
            self.widget.nextPreviewButton.hide()
            self.widget.prevPreviewButton.hide()
            return

        if len(previewFilenames) > 1:
            self.widget.nextPreviewButton.show()
            self.widget.prevPreviewButton.show()
        else:
            self.widget.nextPreviewButton.hide()
            self.widget.prevPreviewButton.hide()

        self.showPreview(previewFilenames[self.curPreviewFilenameIdx], autoLoadBigFiles=self.autoLoadBigFiles)