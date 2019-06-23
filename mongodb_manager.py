import pymongo

class MongoDBManager:
    def __init__(self, host, databaseName):
        self.host = host
        self.databaseName = databaseName
        self.client = pymongo.MongoClient(host)
        self.db = self.client[databaseName]

    # entry: dictionary
    def insertOne(self, collectionName, entry):
        self.db[collectionName].insert_one(entry)

    def getCollectionNames(self):
        return self.db.list_collection_names()

    def insertExampleEntries(self):
        self.insertOne("test", { "name": "John", "address": "Highway 37" })
        self.insertOne("test", { "name": "Bob", "address": "Highway 37" })
        self.insertOne("test", { "name": "Kevin", "address": "Highway 35" })