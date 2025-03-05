import os
import pydash
import json
import logging
import pandas

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from src.api.model import Strategy
from src.proxy.fastapi import FastApi
from src.const import STRATEGY_AGENT_ID, RESEARCH_FORMAT_AGENT_ID
from src.monitor.model import BrowserPluginMonitorAgent
from src.utils.content import check_valid_json, list_dict_to_markdown

mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:47017")
db_name = os.environ.get("MONGO_DATABASE", "test")

fast_api = FastApi()

logger = logging.getLogger(__name__)




async def filled_doc(strategy: Strategy) -> dict:
    content = strategy.content
    result = await fast_api.run_agent(agent_id=STRATEGY_AGENT_ID, task=content)
    research_result = pydash.get(result, 'data.result')
    research_result = research_result.replace("```json", "").replace("```", "")
    if not check_valid_json(research_result):
        logger.info(f"Research result {research_result}")
        result_json = {
            "isAction": False,
            "actionContent":"",
            "isResearch": False,
            "researchContent": ""
        }
    else:
        result_json = json.loads(research_result)
    doc = {
        "name": strategy.name,
        "content": strategy.content,
        "description": strategy.description,
        "llm": {
            "is_action": True if result_json["isAction"] == "true" else False,
            "action_content": result_json["actionContent"],
            "is_research": True if result_json["isResearch"] == "true" else False,
            "research_content": result_json["researchContent"],
        },
        "status": "active"
    }
    return doc


class StrategyServer:

    def __init__(self):
        self.db = AsyncIOMotorClient(mongo_uri)[db_name]
        self.collection = self.db["strategies"]

    async def create_strategies(self, strategy: Strategy):
        doc = await filled_doc(strategy)
        doc["_id"] = ObjectId()
        await self.collection.insert_one(doc)
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        return doc

    async def update_strategies(self, strategy: Strategy):
        doc = await filled_doc(strategy)
        await self.collection.update_one({"_id": ObjectId(strategy.id)}, {"$set": doc})
        doc["id"] = strategy.id
        return doc

    async def delete_strategies(self, strategy_id: str):
        await self.collection.find_one_and_update({"_id": ObjectId(strategy_id)}, {"$set": {"status": "deleted"}})
        return {"result": "success"}



    async def list_strategies(self):
        cursor = self.collection.find({"status":{"$ne":"deleted"}}).sort("_id", -1)
        strategies = []
        async for doc in cursor:
            # Convert ObjectId to string
            doc['id'] = str(doc['_id'])
            del doc['_id']  # Remove the ObjectId field
            strategies.append(doc)
        return {
            "data": strategies
        }

    async def run_strategy(self, strategy_id: str, plugin_instance: BrowserPluginMonitorAgent, user_id: str):
        strategy_doc = await self.collection.find_one({"_id": ObjectId(strategy_id)})
        logger.info(f"{strategy_id} -> {strategy_doc['name']}")
        token = None
        result_json = {}
        if strategy_doc is None:
            raise Exception(f"Strategy {strategy_id} not found")
        
        # Convert ObjectId to string for serialization
        strategy_doc['id'] = str(strategy_doc['_id'])
        del strategy_doc['_id']


        if strategy_doc["llm"]["is_research"]:
            task = f'{strategy_doc["llm"]["research_content"]}'
            result = await fast_api.run_agent(agent_id=RESEARCH_FORMAT_AGENT_ID, task=task)
            research_result = pydash.get(result, 'data.result')
            research_result = research_result.replace("```json", "").replace("```", "")
            if not check_valid_json(research_result):
                logger.info(f"Research result {research_result}")
                return research_result
            result_json = json.loads(research_result)
            dataframe_id = result_json["dataframe_id"]
            query_result = await fast_api.tsdb_query(user_id, dataframe_id)
            dataframe_data = pydash.get(query_result, 'data.dataframe.data')
            token = pydash.get(dataframe_data, '0.token')
            if not strategy_doc["llm"]["is_action"]:
                df = pandas.DataFrame(dataframe_data)
                ## 如果存在 timestamp 列则过滤掉 timestamp 的列
                if 'timestamp' in df.columns:
                    df = df.drop(columns=['timestamp'])
                ## 只保留前面两列，且过滤掉 none，nan
                df = df.dropna(axis=1, how='any')
                df = df.iloc[:, :3]
                dataframe_list = list(df.to_dict(orient='records'))

                dataframe_content = list_dict_to_markdown(dataframe_list)
                return dataframe_content


        if strategy_doc["llm"]["is_action"]:
            task = f'{strategy_doc["llm"]["action_content"]}, the token name : {token}' if token else strategy_doc["llm"]["action_content"]
            await plugin_instance.status_queue.put(task)
        return {
            "strategy": strategy_doc,
            "result": result_json,
            "report": pydash.get(result_json, "report")
        }

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    db = AsyncIOMotorClient(mongo_uri)[db_name]
    db["test"].insert_one({"test":1})





