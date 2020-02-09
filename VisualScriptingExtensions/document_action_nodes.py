from VisualScripting.node_exec.base_nodes import ExecuteNode

ACTIONS_IDENTIFIER = "Document Actions"

class DocumentActionNode(ExecuteNode):
    __identifier__ = ACTIONS_IDENTIFIER
    NODE_NAME = 'Document Action'

    def __init__(self):
        super(DocumentActionNode, self).__init__()

        self.add_text_input('category', 'Category', tab='widgets')
        self.add_text_input('tags', 'Tags', tab='widgets')

        self.add_input('document')
        self.add_output('document')

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
    def execute(document):
        return document