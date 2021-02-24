from VisualScripting.node_exec.base_nodes import ExecuteNode
from VisualScriptingExtensions.action_nodes import ActionNode

ACTIONS_IDENTIFIER = "Document Actions"

class DocumentActionNode(ActionNode):
    __identifier__ = ACTIONS_IDENTIFIER
    NODE_NAME = 'Document Action'

    def __init__(self):
        super().__init__(createActionOutput=False)

        self.add_input('document')
        self.add_output('document')

    @staticmethod
    def execute(document):
        return document