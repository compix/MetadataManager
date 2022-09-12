import typing

class MetadataManagerSubmissionTaskSettings(object):
    def __init__(self, dataDict: dict) -> None:
        super().__init__()

        self.dataDict = dataDict

    @property
    def actionId(self) -> str:
        return self.dataDict.get('action_id')

    @actionId.setter
    def actionId(self, value: str):
        self.dataDict['action_id'] = value

    @property
    def name(self) -> str:
        return self.dataDict.get('name')

    @name.setter
    def name(self, value: str):
        self.dataDict['name'] = value

    @property
    def taskType(self) -> str:
        return self.dataDict.get('task_type')

    @taskType.setter
    def taskType(self, value: str):
        self.dataDict['task_type'] = value

    @property
    def outputFilenamesDict(self) -> typing.Dict[str, str]:
        return self.dataDict.get('output_filenames') or dict()

    @outputFilenamesDict.setter
    def outputFilenamesDict(self, value: typing.Dict[str, str]):
        self.dataDict['output_filenames'] = value