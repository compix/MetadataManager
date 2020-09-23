from enum import Enum

class ApplicationMode(Enum):
    GUI = 'GUI'
    Console = 'Console'

    def __str__(self):
        return self.value