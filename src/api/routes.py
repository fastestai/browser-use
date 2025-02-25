import asyncio
import json
import pydash
import logging
import time
import base64
import zlib

from fastapi import FastAPI, APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from src.action.action_agent_manger.server import ActionAgentManager
from src.action.models import ActionAgentConfig
from src.monitor.model import BrowserPluginMonitorAgent
from src.monitor.server import MonitorService
from src.proxy.fastapi import AIService
from src.api.model import ActionResultRequest, ActionRequest, CheckTradeActionRequest, CheckTargetPageRequest, BrowserActionNlpRequest, BrowserActionNlpResponse, ChatMessage, AgentRegisterRequest
from src.action.models import CheckTradeAction, IsTargetPage
from src.prompt import CHECK_TRADE_ACTION, CHECK_TARGET_PAGE
from src.utils.llm import call_llm
from src.const import GPT_ID, ANALYZE_AGENT_ID, EXECUTION_AGENT_ID, RESEARCH_AGENT_ID

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Browser Actions"])
public_router = APIRouter(
    tags=["Tool"]  # 设置 API 分组标签为 Tool
)
monitor_service = MonitorService()
app = FastAPI()
gpt_service = AIService()

action_agent_manager = ActionAgentManager()


@router.post("/action/result")
async def action_result(request: ActionResultRequest):
    try:
        chat_request_id = request.chat_request_id
        action_agent_conf = ActionAgentConfig(task='', llm=None)
        action_agent = action_agent_manager.get_agent(chat_request_id, action_agent_conf)
        # 2. 调用模型获取下一步动作
        # 这里需要实例化您的 LLM 和 Agent
        # 注意：这部分可能需要根据您的具体需求进行调整
        result = await action_agent.set_action_result(result=request.result)
        return result
    except Exception as e:
        logger.error("action result err:", e)
        raise HTTPException(status_code=500, detail=str(e))

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
        # 如果数据是 base64 编码的（通常 pako 压缩后会进行 base64 编码）
        decoded_data = base64.b64decode(request.compressed_data)

        # 解压数据
        # wbits=15+32 表示使用 zlib 格式并自动检测 gzip 头
        decompressed_data = zlib.decompress(decoded_data, wbits=15 + 32)

        # 将字节转换为字符串
        result = decompressed_data.decode('utf-8')
        json_res = json.loads(result)
        start_time = time.time()
        chat_request_id = json_res["chat_request_id"]
        action_agent_conf = ActionAgentConfig(task=json_res["task"],llm=None)
        action_agent = action_agent_manager.get_agent(chat_request_id, action_agent_conf)
        model_output = await action_agent.get_next_actions(json_res["dom_tree"], json_res["url"], json_res["title"], json_res["tabs"])
        end_time = time.time()
        logger.info(f"get next action time: {end_time - start_time}")
        return model_output
    except Exception as e:
        logger.error(f"action result err: {e}")
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
        result = await call_llm(
            system_content=CHECK_TRADE_ACTION,
            human_content=f"""\n NLP: {request.nlp} \n""",
            schema=CheckTradeAction
        )
        return result
    except Exception as e:
        logger.error(f"check trade action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check_target_page")
async def check_target_page(request: CheckTargetPageRequest):
    try:
        result = await call_llm(
            system_content=CHECK_TARGET_PAGE,
            human_content=f"""\n Current url: {request.current_page_url}""",
            schema=IsTargetPage
        )
        return result
    except Exception as e:
        logger.error(f"check target page error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/register")
async def register_agent(request: AgentRegisterRequest):
    """SSE endpoint for monitoring agent progress"""
    agent_id = request.agent_id
    if agent_id in monitor_service.agents:
        logger.info("agent already register")
        return
    create_gpt_result = await gpt_service.create_gpt_user()
    logger.info(f"create user result: {create_gpt_result}")
    user_id =create_gpt_result.data["user_id"]
    logger.info(f"user id: {user_id}")
    monitor_agent = BrowserPluginMonitorAgent(browser_plugin_id=agent_id, gpt_user_id=user_id)
    monitor_service.register_agent(agent_id, monitor_agent)
    return {"user_id": user_id}


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
    agents = monitor_service.get_agents()
    match_agent = pydash.find(agents.values(), lambda a: a.get_gpt_user_id() == user_id)

    if match_agent is None:
        logger.error("agent not found")
        raise HTTPException(
            status_code=500, 
            detail="Monitor Agent not found"
        )
    await match_agent.status_queue.put(content)
    return BrowserActionNlpResponse(
        status="success",
        message=f"start action: {content}"
    )

@router.post("/chat")
async def chat(request: ChatMessage):
    try:
        # 设置超时时间为60分钟
        timeout = 3600  # 秒
        async with asyncio.timeout(timeout):  # 使用 asyncio.timeout 上下文管理器
            gpt_id = GPT_ID

            co_instance_id = request.co_instance_id
            if co_instance_id not in monitor_service.get_agents():
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process chat message: agent not found"
                )
            browser_plugin_instance = monitor_service.get_agent(co_instance_id)
            gpt_user_id = browser_plugin_instance.get_gpt_user_id()
            
            content = f"user message: {request.content}"
            
            check_trade_action_content = CheckTradeActionRequest(nlp=request.content)
            check_result = await check_trade_action(check_trade_action_content)
            agent_ids = [EXECUTION_AGENT_ID]
            if not check_result["parsed"].is_trade_action:
                agent_ids = [RESEARCH_AGENT_ID, ANALYZE_AGENT_ID]
                content += '\n response format: if output contain table list, return markdown format'
            # 在调用 get_chat_response 时传入超时参数
            # response = await fastapi.get_chat_response(
            #     gpt_user_id,
            #     content,
            #     gpt_id,
            #     agent_ids=agent_ids
            # )
                response = await fastapi.run_agent(agent_id=RESEARCH_AGENT_ID, task=content)
                response_content = pydash.get(response.data, 'result')

                if not response.success:
                    raise HTTPException(
                        status_code=500,
                        detail=response.error
                    )
            else:
                content = f'user message: {check_result["parsed"].action} {check_result["parsed"].amount} {check_result["parsed"].coin_name}'
                await browser_plugin_instance.status_queue.put(content)
                response_content = ''
            return response_content

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,  # 使用 504 Gateway Timeout
            detail=f"Request timed out after {timeout} seconds"
        )
    except Exception as e:
        logger.error(f"Exception: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )

# app.include_router(router)
app.include_router(public_router)