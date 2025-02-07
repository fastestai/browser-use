from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

from browser_use.agent.prompts import SystemPrompt
from src.api.services.api_service import ApiService
from langchain_openai import ChatOpenAI  # 或其他您使用的LLM
from browser_use.browser.views import BrowserState, BrowserStateHistory, TabInfo
from langchain_core.messages import HumanMessage, SystemMessage




router = APIRouter()

class ActionRequest(BaseModel):
    dom_tree: dict  # 用于接收消息历史
    task: str
    url: str
    title: str
    tabs: List[TabInfo]

class CheckTargetPageRequest(BaseModel):
    current_page_url: str

class PlanRequest(BaseModel):
    llm: str

class Step(BaseModel):
    step_on: int
    step_llm: str

class Steps(BaseModel):
    steps: List[Step]

class IsTargetPage(BaseModel):
    result: bool

class CheckTradeActionRequest(BaseModel):
    nlp: str

class CheckTradeAction(BaseModel):
    is_trade_action: bool
    action: str
    coin_name: str
    amount: float


@router.post("/get_next_action")
async def get_next_action(request: ActionRequest):
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


@router.post("/get_plan")
async def get_plan(request: PlanRequest):
    try:
        llm = ChatOpenAI(model_name="gpt-4o-mini")
        plan_message = f"""{request.llm}"""
        structured_llm = llm.with_structured_output(schema=Steps, include_raw=True, method="function_calling")
        result = await structured_llm.ainvoke(plan_message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check_trade_action")
async def check_trade_action(request: CheckTradeActionRequest):
    try:
        llm = ChatOpenAI(model_name="gpt-4o-mini")
        plan_message = """
            You are a precise browser automation agent that interacts with websites through structured commands. Your role is to:
        1. Analyze the provided NLP action
        2. Determine if the behavior described by the NLP is trading cryptocurrencies. For example, it should be a description of the sale, the crypto coins bought and sold, and the number of coins bought and sold
        3. Respond with valid JSON containing the result of determine

        INPUT STRUCTURE:
        NLP: the provided action description 

        RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format: 
        {"is_trade_action": true, "action":"buy", "coin_name":"trump", "amount":0.01}
            """
        system_message = SystemMessage(content=plan_message)
        human_message = HumanMessage(content=f"""
            NLP: {request.nlp}
            """)

        msg = [system_message, human_message]

        structured_llm = llm.with_structured_output(schema=CheckTradeAction, include_raw=True, method="function_calling")
        result = await structured_llm.ainvoke(msg)
        print(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check_target_page")
async def check_target_page(request: CheckTargetPageRequest):
    try:
        llm = ChatOpenAI(model_name="gpt-4o-mini")
        plan_message = """
            You are a precise browser automation agent that interacts with websites through structured commands. Your role is to:
        1. Analyze the provided webpage url
        2. Determine if you are already on the target page https://gmgn.ai
        3. Respond with valid JSON containing the result of determine

        INPUT STRUCTURE:
        Current URL: The webpage you're currently on 

        RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format: 
        {"result": true}
            """
        system_message = SystemMessage(content=plan_message)
        human_message = HumanMessage(content=f"""
            Current url: {request.current_page_url}
            """)

        msg = [system_message, human_message]

        structured_llm = llm.with_structured_output(schema=IsTargetPage, include_raw=True, method="function_calling")
        result = await structured_llm.ainvoke(msg)
        print(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))