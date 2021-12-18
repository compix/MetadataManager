from VisualScripting.node_exec.base_nodes import ExecuteNode
from VisualScripting.node_exec.base_nodes import defNode

ACTIONS_IDENTIFIER = "Actions"

class ActionNode(ExecuteNode):
    __identifier__ = ACTIONS_IDENTIFIER
    NODE_NAME = 'Action'

    def __init__(self, createActionOutput=True):
        super().__init__()

        self.add_text_input('category', 'Category', tab='widgets')
        self.add_text_input('tags', 'Tags', tab='widgets')
        self.add_checkbox(name='runsOnMainThread', label='', text='Run On Main Thread', state=False, tab='widgets')

        if createActionOutput:
            self.add_input('action')
            self.add_output('action')

    @property
    def category(self):
        return '{!r}'.format(self.get_property('category'))

    @property
    def runsOnMainThread(self):
        return self.get_property('runsOnMainThread')

    @property
    def filterTags(self):
        tagsString = self.get_property('tags')
        tags = tagsString.split(',')
        nonEmptyTags = []
        for tag in tags:
            if tag != None and tag != '' and not tag.isspace():
                nonEmptyTags.append(f"\"{tag}\"")

        fixedTagsString = ','.join(nonEmptyTags)
        return f'[{fixedTagsString}]'

    @property
    def constantArgs(self):
        return []

    @staticmethod
    def execute(action=None):
        return action

@defNode('updateActionProgress', isExecutable=True, identifier=ACTIONS_IDENTIFIER)
def updateActionProgress(action, progress: float, progressMessage: str):
    action.updateProgress(progress, progressMessage)