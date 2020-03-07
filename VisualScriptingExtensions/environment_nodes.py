from VisualScripting.node_exec.base_nodes import defNode, defInlineNode, InlineNode
from MetadataManagerCore.environment.EnvironmentManager import EnvironmentManager
from VisualScripting.NodeGraphQt.base import node

ENVIRONMENT_MANAGER : EnvironmentManager = None
IDENTIFIER = "Environment"

@defNode("Environment Settings", isExecutable=False, returnNames=["Settings Dictionary"], identifier=IDENTIFIER)
def getEnvironmentSettings(environmentName):
    if ENVIRONMENT_MANAGER != None:
        env = ENVIRONMENT_MANAGER.getEnvironmentFromName(environmentName)
        return env.getEvaluatedSettings() if env != None else None
    else:
        return None

class EnvironmentSelectionNode(InlineNode):
    __identifier__ = IDENTIFIER
    NODE_NAME = 'Select Environment'

    def __init__(self):
        super(EnvironmentSelectionNode,self).__init__()

        self.comboBoxNodeWidget = self.add_combo_menu("environmentComboMenu", "Environment")
        self.add_output('Name')

        self.add_button("Refresh", self.onRefresh)
        self.onRefresh()

    def onRefresh(self):
        curSelection = self.get_property('environmentComboMenu')
        self.comboBoxNodeWidget.clear()

        if ENVIRONMENT_MANAGER != None:
            envNames = ENVIRONMENT_MANAGER.getEnvironmentNames()
            self.comboBoxNodeWidget.add_items(envNames)

            self.deleteProperty("environmentComboMenu")
            self.create_property("environmentComboMenu", envNames[0] if len(envNames) > 0 else None, items=envNames, widget_type=node.NODE_PROP_QCOMBO)

            if curSelection != None:
                idx = envNames.index(curSelection)
                if idx >= 0:
                    self.comboBoxNodeWidget.widget.setCurrentIndex(idx)

    def getInlineCode(self):
        return '{!r}'.format(self.get_property('environmentComboMenu'))