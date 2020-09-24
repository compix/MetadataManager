import json
import os

class AppRepositoryInfo(object):
    def __init__(self, repositoryDir: str) -> None:
        super().__init__()

        self.directory = repositoryDir

        with open(self.infoFilename) as f:
            self.infoDict = json.load(f)

    @property
    def latestVersionBasename(self):
        return self.infoDict['latest']

    @property
    def latestVersionFilename(self):
        return os.path.join(self.directory, self.latestVersionBasename)

    @property
    def infoFilename(self):
        return os.path.join(self.directory, 'info.json')

    def update(self, modificationDict: dict):
        for key, value in modificationDict.items():
            self.infoDict[key] = value
                
        with open(self.infoFilename, 'w') as f:
            json.dump(self.infoDict, f, indent=4, sort_keys=True)

    def updateLatestVersion(self, latestVersionFilename: str):
        basename = os.path.basename(latestVersionFilename)
        self.update({'latest': basename})