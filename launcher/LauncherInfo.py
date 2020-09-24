import json
import os

class LauncherInfo(object):
    def __init__(self, launcherDir: str) -> None:
        super().__init__()

        self.directory = launcherDir

        with open(self.launcherInfoFilename) as f:
            self.infoDict = json.load(f)

    @property
    def appRepositoryDirectory(self):
        return self.infoDict['app_repository_dir']

    @property
    def exeName(self):
        return self.infoDict['exe_name']

    @property
    def currentVersionFilename(self):
        return self.infoDict.get('current_version_filename')

    @property
    def launcherInfoFilename(self):
        return os.path.join(self.directory, 'launcher.json')

    @property
    def appFolderName(self):
        return self.infoDict['app_folder_name']

    def update(self, modificationDict: dict):
        for key, value in modificationDict.items():
            self.infoDict[key] = value
                
        with open(self.launcherInfoFilename, 'w') as f:
            json.dump(self.infoDict, f, indent=4, sort_keys=True)

    def updateCurrentVersionFilename(self, filename: str):
        self.update({'current_version_filename': filename})