from VisualScripting.node_exec.base_nodes import ExecuteNode

ACTIONS_IDENTIFIER = "Actions"

class ActionNode(ExecuteNode):
    __identifier__ = ACTIONS_IDENTIFIER
    NODE_NAME = 'Action'

    def __init__(self):
        super().__init__()

        self.add_text_input('category', 'Category', tab='widgets')
        self.add_text_input('tags', 'Tags', tab='widgets')

    @property
    def category(self):
        return '{!r}'.format(self.get_property('category'))

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

    @staticmethod
    def execute():
        pass