from typing import Optional, Dict, Any, List
import aiohttp
import json
import logging
from datetime import datetime
from pydantic import BaseModel
import asyncio

logger = logging.getLogger(__name__)

class ApiResponse(BaseModel):
    """Base model for API responses"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class FastApi:
    """External API service for making HTTP requests"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the external API service
        
        Args:
            api_key: API key for authentication (if required)
        """
        self.base_url = 'https://api.fastest.ai'
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        # 设置默认超时时间（秒）
        self.timeout = aiohttp.ClientTimeout(total=3600)

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=self.timeout  # 添加超时设置
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None  # 允许单个请求覆盖默认超时
    ) -> ApiResponse:
        """
        Send HTTP request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: URL parameters
            timeout: Request timeout in seconds
        """
        await self._ensure_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        print("url", url)
        print("data", data)

        # 使用请求特定的超时或默认超时
        request_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else self.timeout

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=request_timeout
            ) as response:
                response_data = await response.json()
                print(response_data)
                print("response_data", response_data)
                
                if response.status >= 400:
                    return ApiResponse(
                        success=False,
                        error=f"API error: {response.status} - {response_data.get('message', 'Unknown error')}"
                    )
                
                return ApiResponse(
                    success=True,
                    data=response_data
                )
                
        except asyncio.TimeoutError:
            logger.error("Request timed out")
            return ApiResponse(
                success=False,
                error="Request timed out"
            )
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return ApiResponse(
                success=False,
                error=f"Request failed: {str(e)}"
            )

    async def get_chat_response(self, user_id: str, content: str, gpt_id: str, agent_ids: Optional[List[str]] = []) -> ApiResponse:
        """
        Get chat response from API
        
        Args:
            user_id: User identifier
            content: Message content
            gpt_id: GPT model identifier
        """
        data = {
            "messages": [{
                "content": content,
                "role": "user",
                "timestamp": int(datetime.now().timestamp())
            }],
            "user_id": user_id,
            "gpt_id": gpt_id,
            "use_agent": True
        }
        if len(agent_ids)>0:
            data.update({"team": {"agent_ids": agent_ids}})

        return await self._request("POST", "/v2/chat", data=data)

    async def create_gpt_user(self):
        """Create a new GPT user"""
        data = {}
        return await self._request("POST", "/v1/user/create", data=data)


    async def create_gpt(self):
        data = {
          "name": "string",
          "profile": {
            "persona": "You are a professional meme coin trader"
            }
        }
        return await self._request("POST",'/v1/gpt/create', data=data)

    async def create_agent(self, agent_conf: dict, gpt_id: str):
        agent_conf.update({'gpt_id': gpt_id})
        data ={
            "agent_config": agent_conf
        }
        print(agent_conf)
        return await self._request("POST", '/v1/agent/create', data=data)

    async def gpt_register_tool(self, gpt_id: str):
        data ={
            "tools_config": {
                "gpt_id": gpt_id,
                "host": "http://43.134.24.146:18000",
                "openapi_config": {"openapi":"3.1.0","info":{"title":"API Service","version":"0.1.0"},"paths":{"/api/v1/tool/browser_action_nlp":{"post":{"tags":["Tool"],"summary":"Browser Action Nlp","description":"Process natural language browser action descriptions\n\nThis endpoint receives natural language browser operation instructions \nand forwards them to the corresponding monitoring agent.\n\nParameters:\n    request: BrowserActionNlpRequest\n        - context: Context information\n            - gpt_id: GPT model ID\n            - user_id: User ID\n        - content: Natural language description of browser action\n\nReturns:\n    BrowserActionNlpResponse:\n        - status: Execution status (success/error)\n        - message: Execution message with operation details\n\nExample:\n    Request:\n        POST /api/v1/tool/browser_action_nlp\n        {\n            \"context\": {\n                \"gpt_id\": \"67ab0c86880303187f65d3a8\",\n                \"user_id\": \"user_123\"\n            },\n            \"content\": \"Click the login button on the page\"\n        }\n\n    Success Response:\n        {\n            \"status\": \"success\",\n            \"message\": \"start action: Click the login button on the page\"\n        }\n\n    Error Response:\n        {\n            \"detail\": \"Monitor Agent not found\"\n        }\n\nNotes:\n    - Ensure monitoring agent is registered before calling\n    - Natural language description should be clear and specific\n    - Valid GPT ID and user ID are required","operationId":"browser_action_nlp_api_v1_tool_browser_action_nlp_post","requestBody":{"content":{"application/json":{"schema":{"$ref":"#/components/schemas/BrowserActionNlpRequest"}}},"required":True},"responses":{"200":{"description":"Successfully processed browser action","content":{"application/json":{"schema":{"$ref":"#/components/schemas/BrowserActionNlpResponse"},"example":{"status":"success","message":"start action: Click the login button on the page"}}}},"422":{"description":"Validation Error","content":{"application/json":{"schema":{"$ref":"#/components/schemas/HTTPValidationError"}}}}}}}},"components":{"schemas":{"BrowserActionNlpRequest":{"properties":{"context":{"$ref":"#/components/schemas/ContextRequest","description":"Context information"},"content":{"type":"string","minLength":1,"title":"Content","description":"Natural language description of browser action","example":"Click the login button on the page"}},"type":"object","required":["context","content"],"title":"BrowserActionNlpRequest","description":"Request model for browser action natural language processing"},"BrowserActionNlpResponse":{"properties":{"status":{"type":"string","enum":["success","error"],"title":"Status","description":"执行状态","example":"success"},"message":{"type":"string","title":"Message","description":"执行消息","example":"start action: 点击页面上的登录按钮"}},"type":"object","required":["status","message"],"title":"BrowserActionNlpResponse","description":"浏览器动作执行响应"},"ContextRequest":{"properties":{"gpt_id":{"type":"string","title":"Gpt Id"},"user_id":{"type":"string","title":"User Id","description":"user id"}},"type":"object","required":["user_id"],"title":"ContextRequest"},"HTTPValidationError":{"properties":{"detail":{"items":{"$ref":"#/components/schemas/ValidationError"},"type":"array","title":"Detail"}},"type":"object","title":"HTTPValidationError"},"ValidationError":{"properties":{"loc":{"items":{"anyOf":[{"type":"string"},{"type":"integer"}]},"type":"array","title":"Location"},"msg":{"type":"string","title":"Message"},"type":{"type":"string","title":"Error Type"}},"type":"object","required":["loc","msg","type"],"title":"ValidationError"}}}}
            }
        }
        return await self._request("POST", '/v1/gpt/register_tools', data=data)

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Async context manager entry point"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit point"""
        await self.close()


async def main():
    # gpt_id = "67acc197140b250260ff8b68"


    agent_configs = [
    {
      "name": "researcher_agent",
      "description": "Conduct research and analysis if necessary. Can be called multiple times.",
      "system_message": "### Role Description\nYou are a researcher based on the user's instruction to generate a research report. Only proceed when delegated.\n### Workflow\n1. Understand the user instruction\n2. Conduct research based on the research plan from researcher_planning_agent\n3. Generate the research report\n### Input\n* research plan from researcher_planning_agent\n### Output\n1. On top, tell me your execution plan\n2. Pass your report to the next agent [\"trends\"]",
      "model": "openai/gpt-4o-2024-11-20",
      "tools":["trends"]
    },
    {
      "name": "reply_agent",
      "description": "Gather the result from the previous agent, answer the question from the user instruction.",
      "system_message": "### Role Description\nYour goal is to provide clear, accurate, and easy-to-understand answers to user inquiries, drawing upon the information provided in the research report.\n### Workflow\n1. Receive the result from the previous agent\n2. Receive the user's question or instruction (user_instruction).\n3. Acknowledge the user's question by restating it to ensure you understand their needs.\n4. Based on the research report, craft a detailed and helpful answer for the user.\n5. Present the answer in a polite, conversational, and easy-to-understand tone, as if engaging in a one-on-one conversation.\n### Input\n* result from the previous agent\n* user_instruction: The user's question or request.\n### Output\nYour reply should follow this format to ensure clarity and a positive user experience:\n* **[Confirmation]:** Begin by restating the user's question or request to confirm your understanding. For example: \"Thank you for your question! I understand you'd like to know...\"\n* **[Answer]:** Provide a direct and concise answer to the user's question, based on the research report.\n* **[Explanation]:** Elaborate on your answer, providing context, reasoning, and any relevant details from the research report. Mention any specific tools, approaches, or methodologies used in the research that support your answer. The goal is to make the answer as clear and helpful as possible.\n* **[Closing]:** End with a polite closing, such as: \"I hope this helps! Please let me know if you have any further questions.\" or \"We're here to assist you further if needed.\"\n\nIf there contains a list of items, Return as a table list in Markdown format.",
      "model": "openai/gpt-4o-2024-11-20"
    },
    {
      "name": "execution_agent",
      "description": "Call tool by user provide action trade nlp. Work depends on whether called according to user instruction.",
      "system_message": "### Role Description\nYou are a professional trading agent who calls action tools. You are idle unless you are required to work by user instruction.\n### Workflow\n1. Build the request by the request schema of the tool and execution action by user-provided action trade nlp\n2. Call the tool\n3. Wait for the operation result\n### Input\n* nlp from the user\n### Output\n* action result and format as the response schema of the tool\n* reply including:\nTrade Execution Parameters:\n- Token: SEXCOIN (highest percentage increase)\n- Platform: gmgn.ai (Solana blockchain)\n- Purchase Amount: 0.01 share\n- Current Token Details:\n* Price: Approximately $0.00 (micro-price range)\n* 24h Volume: $182.7K\n* Price Increase: +3,200%",
      "model": "openai/gpt-4o-2024-11-20",
      "tools":["browser_action_nlp"]
    }
  ]
    fastapi = FastApi()
    # gpt_id = await fastapi.create_gpt()
    # print("gpt_id", gpt_id)
    # gpt_user_id = await fastapi.create_gpt_user()
    # print(gpt_user_id)
    gpt_id = '67af1045db80df16e4b1880f'
    gpt_user_id = '67af1064db80df16e4b189c9'
    register_result = await fastapi.gpt_register_tool(gpt_id)
    print("register_result", register_result)
    for c in agent_configs:
        result = await fastapi.create_agent(agent_conf =c, gpt_id=gpt_id)
        print(result)
    # content = 'I buy 0.01 trump'
    # chat_result = await fastapi.get_chat_response(user_id=gpt_user_id,content=content,gpt_id=gpt_id)
    # print(chat_result)
    # for c in agent_configs:
    #     result = await fastapi.create_agent(agent_conf=c, gpt_id=gpt_id)
    #     print(result)


if __name__ == '__main__':
    asyncio.run(main())
