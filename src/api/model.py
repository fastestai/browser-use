from pydantic import BaseModel, Field
from typing import List, Any

from browser_use.browser.views import TabInfo
from browser_use.agent.views import (
    ActionResult
)


class ActionRequest(BaseModel):
    compressed_data: Any
    # dom_tree: dict
    # task: str
    # url: str
    # title: str
    # tabs: List[TabInfo]
    # chat_request_id: str


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
    status: str = Field(
        description="action status",
        example="success",
        enum=["success", "error"]
    )
    message: str = Field(
        description="action message",
        example="start action: click button"
    )

class ChatMessage(BaseModel):
    co_instance_id: str
    content: str
    dataframe: List[dict]

class ChatResponse(BaseModel):
    content: str
    timestamp: float
    status: str


class CheckTargetPageRequest(BaseModel):
    current_page_url: str

class AgentRegisterRequest(BaseModel):
    agent_id: str

class ActionResultRequest(BaseModel):
    chat_request_id: str
    result: ActionResult

class CheckTradeActionRequest(BaseModel):
    nlp: str

class GetContentByImageRequest(BaseModel):
    image_base64: str
    nlp: str
    prompt: str

class SaveStrategyRequest(BaseModel):
    strategy: dict

class UpdateStrategyRequest(BaseModel):
    strategy: dict

class RunStrategyRequest(BaseModel):
    strategy_id: str