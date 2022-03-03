from LauncherInfo import LauncherInfo
from AppRepositoryInfo import AppRepositoryInfo
import shutil
import os
from datetime import datetime
import uuid
from md5 import md5

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

class AppUploader(object):
    def __init__(self, appRepositoryPath: str) -> None:
        super().__init__()
        
        self.repositoryInfo = AppRepositoryInfo(appRepositoryPath)
        
    def generateUniqueFilename(self, ext: str):
        curDateStr = datetime.now().strftime("%d_%m_%Y")

        while True:
            versionHash = str(uuid.uuid4())[:8]
            basename = f'{curDateStr}_{versionHash}{ext}'

            filename = os.path.join(self.repositoryInfo.directory, basename)
            if not os.path.exists(filename):
                return filename

    def generateVersionFilename(self, appFilename: str):
        _, ext = os.path.splitext(appFilename)
        md5Hash = md5(appFilename)
        basename = f'{md5Hash}{ext}'

        filename = os.path.join(self.repositoryInfo.directory, basename)
        return filename

    def uploadApp(self, appFilename: str):
        uploadedVersionFilename = self.generateVersionFilename(appFilename)

        if os.path.exists(uploadedVersionFilename):
            return
            
        shutil.copy(appFilename, uploadedVersionFilename)
        self.repositoryInfo.updateLatestVersion(uploadedVersionFilename)
        
if __name__ == '__main__':
    launcherInfoDir = BASE_PATH
    privateDir = os.path.join(BASE_PATH, '..', 'private')
    if os.path.exists(os.path.join(privateDir, 'launcher.json')):
        launcherInfoDir = privateDir

    launcherInfo = LauncherInfo(launcherInfoDir)
    appUploader = AppUploader(launcherInfo.appRepositoryDirectory)
    appUploader.uploadApp(os.path.abspath(os.path.join(BASE_PATH, '..', 'dist', 'MetadataManager.zip')))