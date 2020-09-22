import json
import os
import logging
import zipfile
import shutil

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

    def versionFromFilename(self, versionFilename: str):
        if versionFilename == None:
            return None

        base, _ = os.path.splitext(os.path.basename(versionFilename))
        return base
        
    def update(self, currentVersionFilename: str, newVersionFilename: str):
        self.logger.info(f'Updating to newest version: {newVersionFilename}...')

        currentVersion = self.versionFromFilename(currentVersionFilename)
        if currentVersion:
            self.deleteLocalVersion(currentVersion)
        
        # Extract:
        newVersion = self.versionFromFilename(newVersionFilename)
        with zipfile.ZipFile(newVersionFilename, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(BASE_PATH, newVersion))

        # Update launcher info:
        with open(self.launcherInfoFilename, mode='r') as f:
            infoDict = json.load(f)
            infoDict['current_version_filename'] = newVersionFilename

        with open(self.launcherInfoFilename, mode='w') as f:
            json.dump(infoDict, f, indent=4, sort_keys=True)

    @property
    def launcherInfoFilename(self):
        return os.path.join(BASE_PATH, 'launcher.json')

    def checkForUpdates(self):
        self.logger.info('Checking for updates...')
        with open(self.launcherInfoFilename) as f:
            launcherInfoDict = json.load(f)
            repositoryDir = launcherInfoDict['app_repository_dir']
            infoFilename = os.path.join(repositoryDir, 'info.json')

        with open(infoFilename) as f:
            infoDict = json.load(f)
            latestVersionFilename = os.path.join(repositoryDir, infoDict['latest'])

        curVersionFilename = launcherInfoDict.get('current_version_filename')
        if curVersionFilename == None or curVersionFilename != latestVersionFilename:
            self.update(curVersionFilename, latestVersionFilename)
        else:
            self.logger.info('Already up to date.')

    def currentVersion(self):
        with open(self.launcherInfoFilename) as f:
            launcherInfoDict = json.load(f)
            return self.versionFromFilename(launcherInfoDict['current_version_filename'])

    def startApp(self):
        with open(self.launcherInfoFilename) as f:
            launcherInfoDict = json.load(f)
            currentVersion = self.versionFromFilename(launcherInfoDict['current_version_filename'])
            exeName = launcherInfoDict['exe_name']

        exeFilename = os.path.join(BASE_PATH, currentVersion, exeName)
        os.startfile(os.path.normpath(exeFilename))

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