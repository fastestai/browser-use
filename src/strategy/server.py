import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
db_name = os.environ.get("MONGO_DATABASE", "test")




class StrategyServer:

    def __init__(self):
        self.db = AsyncIOMotorClient(mongo_uri)[db_name]
        self.collection = self.db["strategies"]

    def create_strategies(self, doc: dict):
        self.collection.insert_one(doc)

    def update_strategies(self, doc: dict):
        self.collection.update_one({"_id": doc["_id"]}, {"$set": doc})

    def list_strategies(self):
        return self.collection.find()

    def run_strategy(self, strategy_id: str):
        strategy_doc = self.collection.find_one({"_id": strategy_id})
        if strategy_doc is None:
            raise Exception(f"Strategy {strategy_id} not found")
        strategy = strategy_doc["strategy"]
        return strategy





