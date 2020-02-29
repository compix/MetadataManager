"""
AWS Thinkbox Software Deadline nodes
""" 

from VisualScripting.node_exec.base_nodes import defNode, defInlineNode
from MetadataManagerCore.third_party_integrations.deadline_service import DeadlineService, DeadlineServiceInfo

DEADLINE_SERVICE : DeadlineService = None
DEADLINE_IDENTIFIER = "Deadline"

@defNode("Submit Job", isExecutable=True, returnNames=["Job Dict"], identifier=DEADLINE_IDENTIFIER)
def submitJob(jobInfoFilename, pluginInfoFilename, auxiliaryFilenames=[]):
    if DEADLINE_SERVICE != None:
        return DEADLINE_SERVICE.submitJob(jobInfoFilename, pluginInfoFilename, auxiliaryFilenames=auxiliaryFilenames)

    return None