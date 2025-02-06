from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from src.api.services.api_service import ApiService
from langchain_openai import ChatOpenAI  # 或其他您使用的LLM
from browser_use.browser.views import BrowserState, BrowserStateHistory, TabInfo



router = APIRouter()

# 示例路由
@router.get("/hello")
async def hello_world():
    return {"message": "Hello, World!"}

# 示例数据模型
class Item(BaseModel):
    name: str
    description: str = None

# POST 请求示例
@router.post("/items")
async def create_item(item: Item):
    return {"item": item}

class MessageRequest(BaseModel):
    dom_tree: dict  # 用于接收消息历史
    task: str
    url: str
    title: str
    tabs: List[TabInfo]

class ActionResponse(BaseModel):
    current_state: Dict[str, Any]
    action: List[Dict[str, Any]]

@router.post("/get_next_action")
async def get_next_action(request: MessageRequest):
    try:
        api_service = ApiService(request.task, ChatOpenAI(model_name="gpt-4o-mini"))
        # 2. 调用模型获取下一步动作
        # 这里需要实例化您的 LLM 和 Agent
        # 注意：这部分可能需要根据您的具体需求进行调整
        model_output = await api_service.get_next_actions(request.dom_tree, request.url, request.title, request.tabs)
        print(model_output)
        return model_output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))