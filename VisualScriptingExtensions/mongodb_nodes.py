from VisualScripting.node_exec.base_nodes import defNode, defInlineNode

DB_MANAGER = None
MONGODB_IDENTIFIER = "MongoDB"

@defNode("Insert Or Modify Document", isExecutable=True, identifier=MONGODB_IDENTIFIER)
def insertOrModifyDocument(collectionName, sid, dataDict, checkForModifications):
    if DB_MANAGER != None:
        checkForModifications = checkForModifications == True or checkForModifications == "True"
        DB_MANAGER.insertOrModifyDocument(collectionName, sid, dataDict, checkForModifications)
    else:
        print("DB Manager is None.")