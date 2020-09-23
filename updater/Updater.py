import os
from PySide2 import QtCore
from PySide2.QtWidgets import QMessageBox, QWidget
from qt_extensions import qt_util
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import json
import logging

logger = logging.getLogger(__name__)

class WatchDogFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, watchDog) -> None:
        self.watchDog = watchDog

    def on_created(self, event):
        if self.watchDog.checkExtension(event.src_path):
            self.watchDog.onFileCreated(event.src_path)

    def on_modified(self, event):
        if self.watchDog.checkExtension(event.src_path):
            self.watchDog.onFileModified(event.src_path)

class Updater(FileSystemEventHandler):
    def __init__(self, launcherFilename: str, bootstrapper, mainWindow: QWidget) -> None:
        super().__init__()

        self.launcherFilename = launcherFilename
        self.bootstrapper = bootstrapper
        self.mainWindow = mainWindow
        self.askingToUpdate = False
        self.updateAskTimer = QtCore.QTimer()
        self.updateAskTimer.timeout.connect(self.reopenUpdateDialog)
        self.updateAskTimeInSeconds = 300.0
        self.latestVersionFilename = None

        try:
            self.observer = Observer()
            self.observer.schedule(self, self.repositoryDir, recursive=False)
            self.observer.start()
        except Exception as e:
            logger.error(f'Failed with exception: {str(e)}')

    @property
    def repositoryDir(self):
        with open(self.launcherInfoFilename) as f:
            launcherInfoDict = json.load(f)
            repositoryDir = launcherInfoDict['app_repository_dir']
            return repositoryDir

    @property
    def launcherInfoFilename(self):
        return os.path.join(os.path.dirname(self.launcherFilename), 'launcher.json')

    def shutdown(self):
        self.observer.stop()
        self.observer.join()

    def on_modified(self, event):
        basename = os.path.basename(event.src_path)
        if basename == 'info.json':
            try:
                self.checkForUpdates(event.src_path)
            except Exception as e:
                logger.error(f'Failed with exception: {str(e)}')

    def checkForUpdates(self, infoFilename: str):
        if self.askingToUpdate:
            return

        with open(self.launcherInfoFilename) as f:
            launcherInfoDict = json.load(f)

        with open(infoFilename) as f:
            infoDict = json.load(f)
            latestVersionFilename = os.path.join(self.repositoryDir, infoDict['latest'])

        curVersionFilename = launcherInfoDict.get('current_version_filename')
        if curVersionFilename == None or curVersionFilename != latestVersionFilename:
            # New version available, show dialog.
            self.askingToUpdate = True
            self.latestVersionFilename = latestVersionFilename
            qt_util.runInMainThread(self.openUpdateDialog, latestVersionFilename)

    def reopenUpdateDialog(self):
        self.openUpdateDialog(self.latestVersionFilename)

    def openUpdateDialog(self, latestVersionFilename: str):
        self.updateAskTimer.stop()
        ret = QMessageBox.question(self.mainWindow, f"New Update: {os.path.basename(latestVersionFilename)}", "There is an update available. Update now? (recommended)")
        if ret == QMessageBox.Yes:
            self.bootstrapper.requestUpdate()
        else:
            self.askingToUpdate = False
            self.updateAskTimer.start(self.updateAskTimeInSeconds * 1000)