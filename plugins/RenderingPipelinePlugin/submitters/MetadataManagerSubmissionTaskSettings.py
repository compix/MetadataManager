class MetadataManagerSubmissionTaskSettings(object):
    def __init__(self, actionId: str, name: str, outputFilenamesDict: dict) -> None:
        super().__init__()

        self.actionId = actionId
        self.name = name
        self.outputFilenamesDict = outputFilenamesDict

    @staticmethod
    def fromDict(d: dict):
        return MetadataManagerSubmissionTaskSettings(d.get('action_id', ''), d.get('name', ''), d.get('output_filenames', {}))

    def toDict(self):
        return {
            'action_id': self.actionId,
            'name': self.name,
            'output_filenames': self.outputFilenamesDict
        }