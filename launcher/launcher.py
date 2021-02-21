from LauncherInfo import LauncherInfo
from AppRepositoryInfo import AppRepositoryInfo
import os
import logging
import zipfile
import shutil
import subprocess
import time
import sys

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

class Launcher(object):
    def __init__(self) -> None:
        super().__init__()

        self.initLogging()

    def initLogging(self):
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.DEBUG)

        logging.basicConfig(format='%(asctime)s %(name)s:%(threadName)s %(levelname)s: %(message)s', 
                            datefmt='%H:%M:%S', handlers=[consoleHandler], level=logging.DEBUG)

        self.logger = logging.getLogger(__name__)

    def deleteLocalVersion(self, version: str):
        self.logger.info(f'Deleting local version: {version}...')
        shutil.rmtree(os.path.join(BASE_PATH, version))
        
    def update(self, currentVersionFilename: str, newVersionFilename: str):
        self.logger.info(f'Updating to newest version: {newVersionFilename}...')

        launcherInfo = LauncherInfo(BASE_PATH)

        if currentVersionFilename:
            self.deleteLocalVersion(launcherInfo.appFolderName)
        
        # Extract:
        with zipfile.ZipFile(newVersionFilename, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(BASE_PATH, launcherInfo.appFolderName))

        launcherInfo.updateCurrentVersionFilename(newVersionFilename)

    def checkForUpdates(self):
        self.logger.info('Checking for updates...')
        time.sleep(2.0)

        launcherInfo = LauncherInfo(BASE_PATH)

        repositoryInfo = AppRepositoryInfo(launcherInfo.appRepositoryDirectory)
        curVersionFilename = launcherInfo.currentVersionFilename
        if curVersionFilename == None or curVersionFilename != repositoryInfo.latestVersionFilename or not os.path.exists(self.exeFilename):
            self.update(curVersionFilename, repositoryInfo.latestVersionFilename)
        else:
            self.logger.info('Already up to date.')

    @property
    def exeFilename(self):
        launcherInfo = LauncherInfo(BASE_PATH)
        return os.path.join(BASE_PATH, launcherInfo.appFolderName, launcherInfo.exeName)
        
    def startApp(self):
        subprocess.Popen([os.path.normpath(self.exeFilename), '-launcher', f'{os.path.join(BASE_PATH, sys.argv[0])}'] + sys.argv[1:])

    def run(self):
        try:
            self.checkForUpdates()
            self.startApp()
            return True
        except Exception as e:
            self.logger.error(f'Failed with exception: {str(e)}')
            return False
            

if __name__ == '__main__':
    launcher = Launcher()
    if not launcher.run():
        input('Launcher failed. Please check the output.')