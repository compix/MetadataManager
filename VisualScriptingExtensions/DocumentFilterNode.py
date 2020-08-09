from VisualScripting.node_exec.base_nodes import ExecuteNode

IDENTIFIER = "Filtering"

class DocumentFilterNode(ExecuteNode):
    __identifier__ = IDENTIFIER
    NODE_NAME = 'Document Filter'

    def __init__(self):
        super().__init__()

        self.add_text_input('uniqueLabelName', 'Unique Label Name', tab='widgets')
        self.add_output('document')
        self.add_input('document')
        self.add_input('stringArg')
        self.stringArgOutputPort = self.add_output('stringArg')
        #self.add_checkbox(name='hasStringArg', label='', text='Has String Arg', state=False, tab='widgets')

    @property
    def uniqueLabelName(self):
        return '{!r}'.format(self.get_property('uniqueLabelName'))

    @property
    def hasStringArg(self):
        return len(self.stringArgOutputPort.connected_ports()) > 0
        #return self.get_property('hasStringArg')

    @staticmethod
    def execute(document, stringArg):
        return document, stringArg