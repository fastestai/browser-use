import datetime

from aiohttp import ClientRequest
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, schema_json_of, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_core.messages import BaseMessage
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import pydash

from browser_use.agent.prompts import SystemPrompt
from src.api.services.api_service import ApiService
from langchain_openai import ChatOpenAI  # 或其他您使用的LLM
from browser_use.browser.views import BrowserState, BrowserStateHistory, TabInfo
from langchain_core.messages import HumanMessage, SystemMessage
from src.api.services.monitor_service import MonitorService, BrowserPluginMonitorAgent
from src.api.proxy.fastapi import FastApi


router = APIRouter(include_in_schema=False)
public_router = APIRouter(
    tags=["Tool"]  # 设置 API 分组标签为 Tool
)
monitor_service = MonitorService()

fastapi = FastApi()


class ActionRequest(BaseModel):
    """
    请求下一步动作的数据结构
    """
    dom_tree: dict = Field(
        ...,
        description="DOM树结构",
        example={
            "tag": "html",
            "children": [
                {"tag": "body", "children": []}
            ]
        }
    )
    task: str = Field(
        ...,
        description="要执行的任务描述",
        example="Navigate to the login page"
    )
    url: str = Field(
        ...,
        description="当前页面的URL",
        example="https://example.com"
    )
    title: str = Field(
        ...,
        description="当前页面的标题",
        example="Example Page"
    )
    tabs: List[TabInfo] = Field(
        ...,
        description="浏览器标签页列表"
    )


class ContextRequest(BaseModel):
    gpt_id: str = Field(
        ...,
        description="gpt id",
    ),
    user_id: str = Field(
        ...,
        description="user id"
    )


class BrowserActionNlpRequest(BaseModel):
    """
    Request model for browser action natural language processing
    """
    context: ContextRequest = Field(
        ...,
        description="Context information",
    )
    content: str = Field(
        ...,
        description="Natural language description of browser action",
        example="Click the login button on the page",
        min_length=1
    )

class BrowserActionNlpResponse(BaseModel):
    """
    浏览器动作执行响应
    """
    status: str = Field(
        description="执行状态",
        example="success",
        enum=["success", "error"]  # 限制可能的状态值
    )
    message: str = Field(
        description="执行消息",
        example="start action: 点击页面上的登录按钮"
    )

class ChatMessage(BaseModel):
    """
    Chat message data structure
    """
    co_instance_id: str = Field(
        ...,
        description="Browser instance unique identifier",
        example="39879879878979",
        min_length=1
    )
    content: str = Field(
        ...,
        description="Chat content",
        example="Hello, please help me open example.com",
        min_length=1
    )
    dataframe: List[dict] = Field(
        ...,
        description="Webpages dataframe data"
    )

class ChatResponse(BaseModel):
    """
    聊天响应的数据结构
    """
    content: str = Field(
        description="响应内容",
        example="OK, I'll help you open the webpage"
    )
    timestamp: float = Field(
        description="响应时间戳",
        example=1706443496.789
    )
    status: str = Field(
        description="响应状态",
        example="success",
        enum=["success", "error", "processing"]
    )


class CheckTargetPageRequest(BaseModel):
    current_page_url: str

class PlanRequest(BaseModel):
    llm: str

class AgentRegisterRequest(BaseModel):
    agent_id: str

class Step(BaseModel):
    step_on: int
    step_llm: str

class Steps(BaseModel):
    steps: List[Step]

class IsTargetPage(BaseModel):
    result: bool

class CheckTradeActionRequest(BaseModel):
    """
    检查交易动作的请求结构
    """
    nlp: str = Field(
        ...,
        description="自然语言描述的交易动作",
        example="Buy 0.1 BTC at market price"
    )

class CheckTradeAction(BaseModel):
    """
    交易动作检查的响应结构
    """
    is_trade_action: bool = Field(
        ...,
        description="是否是交易动作"
    )
    action: str = Field(
        ...,
        description="交易类型（买/卖）",
        example="buy"
    )
    coin_name: str = Field(
        ...,
        description="交易的币种名称",
        example="BTC"
    )
    amount: float = Field(
        ...,
        description="交易数量",
        example=0.1
    )

class GetDataframe(BaseModel):
    dataframe: dict


@router.post("/get_next_action")
async def get_next_action(request: ActionRequest):
    """
    获取下一步自动化操作

    参数:
        request: ActionRequest - 包含DOM树和任务信息的请求体

    返回:
        {
            "current_state": {
                "page_summary": "string",
                "evaluation_previous_goal": "string",
                "memory": "string",
                "next_goal": "string"
            },
            "action": [
                {
                    "click_element": {"index": 0},
                    "type_text": {"text": "example"},
                    "press_key": {"key": "Enter"}
                }
            ]
        }

    错误:
        500: 服务器内部错误
    """
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
    """
    检查是否是交易动作并解析详情

    参数:
        request: CheckTradeActionRequest - 包含自然语言描述的交易动作

    返回:
        CheckTradeAction - 解析后的交易动作详情

    示例请求:
        POST /api/check_trade_action
        {
            "nlp": "Buy 0.1 BTC at market price"
        }

    示例响应:
        {
            "is_trade_action": true,
            "action": "buy",
            "coin_name": "BTC",
            "amount": 0.1
        }
    """
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


@router.post("/agent/register")
async def register_agent(request: AgentRegisterRequest):
    """SSE endpoint for monitoring agent progress"""
    agent_id = request.agent_id
    if agent_id in monitor_service.agents:
        return
    # todo production open
    # create_gpt_result = await fastapi.create_gpt_user()
    # user_id =create_gpt_result.data["user_id"]
    user_id = '67ac39d50cef4ea4cf0df45b'
    monitor_agent = BrowserPluginMonitorAgent(browser_plugin_id=agent_id, gpt_user_id=user_id)
    monitor_service.register_agent(agent_id, monitor_agent)
    return


@router.get("/agent/{agent_id}/monitor")
async def monitor_agent(agent_id: str, request: Request):
    """监控特定代理的SSE端点"""
    async def event_generator():
        async for update in monitor_service.get_agent_updates(agent_id):
            if await request.is_disconnected():
                break
            yield json.dumps(update)

    return EventSourceResponse(event_generator())


@public_router.post(
    "/tool/browser_action_nlp",
    response_model=BrowserActionNlpResponse,
    responses={
        200: {
            "description": "Successfully processed browser action",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "start action: Click the login button on the page"
                    }
                }
            }
        }
    }
)
async def browser_action_nlp(request: BrowserActionNlpRequest):
    """
    Process natural language browser action descriptions

    This endpoint receives natural language browser operation instructions 
    and forwards them to the corresponding monitoring agent.

    Parameters:
        request: BrowserActionNlpRequest
            - context: Context information
                - gpt_id: GPT model ID
                - user_id: User ID
            - content: Natural language description of browser action

    Returns:
        BrowserActionNlpResponse:
            - status: Execution status (success/error)
            - message: Execution message with operation details

    Example:
        Request:
            POST /api/v1/tool/browser_action_nlp
            {
                "context": {
                    "gpt_id": "67ab0c86880303187f65d3a8",
                    "user_id": "user_123"
                },
                "content": "Click the login button on the page"
            }

        Success Response:
            {
                "status": "success",
                "message": "start action: Click the login button on the page"
            }

        Error Response:
            {
                "detail": "Monitor Agent not found"
            }

    Notes:
        - Ensure monitoring agent is registered before calling
        - Natural language description should be clear and specific
        - Valid GPT ID and user ID are required
    """
    user_id = request.context.user_id
    content = request.content
    print("content", content)
    print("user_id:", user_id)
    agents = monitor_service.get_agents()
    for agent in agents.values():
        print(agent.get_gpt_user_id())
    match_agent = pydash.find(agents.values(), lambda a: a.get_gpt_user_id() == user_id)

    if match_agent is None:
        raise HTTPException(
            status_code=500, 
            detail="Monitor Agent not found"
        )
    await match_agent.status_queue.put(content)
    return BrowserActionNlpResponse(
        status="success",
        message=f"start action: {content}"
    )




@router.post( "/chat")
async def chat(request: ChatMessage):
    """
    处理用户聊天消息

    本接口用于接收用户的聊天消息，并返回相应的响应。支持普通文本对话和命令处理。

    参数:
        request: ChatMessage
            - co_instance_id: 插件唯一标识，用于跟踪对话上下文
            - content: 聊天内容
            - dataframe: 网页数据
    示例:
        请求:
            POST /api/v1/chat
            {
                "co_instance_id": "co_123",
                "content": "what is the price of BTC",
                "dataframe": {}
            }
    """


    try:
        gpt_id = '67ad8db09d6468c15537fb8c'

        co_instance_id = request.co_instance_id
        if co_instance_id not in monitor_service.get_agents():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process chat message: agent not found"
            )
        browser_plugin_instance = monitor_service.get_agent(co_instance_id)
        gpt_user_id = browser_plugin_instance.get_gpt_user_id()
        
        # 将 dataframe 转换为格式化的字符串
        dataframe_str = json.dumps(request.dataframe, ensure_ascii=False, indent=2)
        content = f'user nlp: {request.content}, dataframe: {dataframe_str}'
        
        print("gpt_user_id", gpt_user_id)
        response = await fastapi.get_chat_response(gpt_user_id, content, gpt_id)
        response_content = pydash.get(response.data, 'content')
        return response_content

        # 根据消息类型处理
       

        # return ChatResponse(
        #     content=response_content,
        #     timestamp=datetime.datetime.now(),
        #     status="success"
        # )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=500,
            detail="Request timed out after 300 seconds"
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


