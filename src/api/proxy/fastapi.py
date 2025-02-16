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
        self.timeout = aiohttp.ClientTimeout(total=36000)

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
                content = await response.read()
                print("content",content)
                response_data = await response.json()
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
        # data = {'messages': [{
        #                          'content': 'user nlp: What tokens can I buy?, dataframe: [\n  {\n    "key": 0,\n    "token": "Broccoli",\n    "age": "17h",\n    "liq-mc": "8.5M $216.5M",\n    "holders": "33.7K",\n    "smart-kol": "- -",\n    "1h-txs": "11,222 6,052 / 5,170",\n    "1h-vol": "$21.4M",\n    "price": "$0.2165",\n    "1m": "+10.5%",\n    "5m": "-1.9%",\n    "1h": "+21.3%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 1,\n    "token": "zhaoling",\n    "age": "2h",\n    "liq-mc": "31.9K $60.9K",\n    "holders": "698",\n    "smart-kol": "- -",\n    "1h-txs": "2,968 1,779 / 1,189",\n    "1h-vol": "$390.8K",\n    "price": "$0.0₄6092",\n    "1m": "+18%",\n    "5m": "-18.2%",\n    "1h": "+74.3%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 2,\n    "token": "MindAi",\n    "age": "3h",\n    "liq-mc": "47K $71.9K",\n    "holders": "1.3K",\n    "smart-kol": "- -",\n    "1h-txs": "1,667 823 / 844",\n    "1h-vol": "$229.9K",\n    "price": "$0.0₄7193",\n    "1m": "+2.3%",\n    "5m": "-21.5%",\n    "1h": "-75.2%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell",\n    "": "Buy"\n  },\n  {\n    "key": 3,\n    "token": "BROCCOLI",\n    "age": "16h",\n    "liq-mc": "635.2K $16.6M",\n    "holders": "7K",\n    "smart-kol": "- -",\n    "1h-txs": "844 406 / 438",\n    "1h-vol": "$624.1K",\n    "price": "$0.0166",\n    "1m": "-2.3%",\n    "5m": "-9.4%",\n    "1h": "-11.2%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "--",\n    "": "Buy"\n  },\n  {\n    "key": 4,\n    "token": "CZBroccoli",\n    "age": "9h",\n    "liq-mc": "34.7K $84.2K",\n    "holders": "1.5K",\n    "smart-kol": "- -",\n    "1h-txs": "761 381 / 380",\n    "1h-vol": "$131.3K",\n    "price": "$0.0₄8425",\n    "1m": "0%",\n    "5m": "+2.2%",\n    "1h": "-55.6%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Buy",\n    "": "Buy"\n  },\n  {\n    "key": 5,\n    "token": "Broccoli",\n    "age": "17h",\n    "liq-mc": "707.7K $4.1M",\n    "holders": "5.2K",\n    "smart-kol": "- -",\n    "1h-txs": "658 309 / 349",\n    "1h-vol": "$414.4K",\n    "price": "$0.0041",\n    "1m": "+2.8%",\n    "5m": "-1.8%",\n    "1h": "-16.1%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 6,\n    "token": "zh zhaoheng",\n    "age": "49m",\n    "liq-mc": "6K $12.4K",\n    "holders": "149",\n    "smart-kol": "- -",\n    "1h-txs": "615 389 / 226",\n    "1h-vol": "$96.9K",\n    "price": "$0.0₄1248",\n    "1m": "-14.1%",\n    "5m": "-14.1%",\n    "1h": "+136.8%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- HODL",\n    "": "Buy"\n  },\n  {\n    "key": 7,\n    "token": "VINU",\n    "age": "84d",\n    "liq-mc": "420.6K $26.6M",\n    "holders": "18.7K",\n    "smart-kol": "- -",\n    "1h-txs": "597 277 / 320",\n    "1h-vol": "$37.5K",\n    "price": "$0.0₇2962",\n    "1m": "+0%",\n    "5m": "+0%",\n    "1h": "-3.4%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced No Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "--",\n    "": "Buy"\n  },\n  {\n    "key": 8,\n    "token": "CaptainBNB",\n    "age": "3d",\n    "liq-mc": "1.6M $23.3M",\n    "holders": "11.4K",\n    "smart-kol": "- -",\n    "1h-txs": "531 257 / 274",\n    "1h-vol": "$332.1K",\n    "price": "$0.0233",\n    "1m": "+0.3%",\n    "5m": "+0.3%",\n    "1h": "+10.4%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 9,\n    "token": "KAKA",\n    "age": "6h",\n    "liq-mc": "136.6K $960K",\n    "holders": "1.1K",\n    "smart-kol": "- -",\n    "1h-txs": "457 288 / 169",\n    "1h-vol": "$180.7K",\n    "price": "$0.0009",\n    "1m": "0%",\n    "5m": "-4.1%",\n    "1h": "-40.9%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 10,\n    "token": "TST",\n    "age": "17d",\n    "liq-mc": "3.9M $119.3M",\n    "holders": "25.4K",\n    "smart-kol": "- -",\n    "1h-txs": "426 219 / 207",\n    "1h-vol": "$336.3K",\n    "price": "$0.1193",\n    "1m": "-0.6%",\n    "5m": "-0.6%",\n    "1h": "+4.2%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- HODL",\n    "": "Buy"\n  },\n  {\n    "key": 11,\n    "token": "CAT",\n    "age": "84d",\n    "liq-mc": "12.5M $121.7M",\n    "holders": "28K",\n    "smart-kol": "- -",\n    "1h-txs": "410 199 / 211",\n    "1h-vol": "$565.5K",\n    "price": "$0.0₄1352",\n    "1m": "+1.7%",\n    "5m": "+1.7%",\n    "1h": "+4.8%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced No Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "--",\n    "": "Buy"\n  },\n  {\n    "key": 12,\n    "token": "BROWNIE",\n    "age": "1d",\n    "liq-mc": "607.9K $1M",\n    "holders": "6.6K",\n    "smart-kol": "- -",\n    "1h-txs": "403 187 / 216",\n    "1h-vol": "$92.1K",\n    "price": "$0.001",\n    "1m": "0%",\n    "5m": "0%",\n    "1h": "-3.9%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "-- Sell All",\n    "": "Buy"\n  },\n  {\n    "key": 13,\n    "token": "Cheems",\n    "age": "84d",\n    "liq-mc": "7.1M $225.5M",\n    "holders": "42.5K",\n    "smart-kol": "1 / -",\n    "1h-txs": "398 205 / 193",\n    "1h-vol": "$282.9K",\n    "price": "$0.0₅1026",\n    "1m": "-0.8%",\n    "5m": "-0.8%",\n    "1h": "+1.7%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced Yes Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "--",\n    "": "Buy"\n  },\n  {\n    "key": 14,\n    "token": "Auction",\n    "age": "83d",\n    "liq-mc": "17.3K $4.7M",\n    "holders": "191",\n    "smart-kol": "- -",\n    "1h-txs": "394 196 / 198",\n    "1h-vol": "$256K",\n    "price": "$11.2018",\n    "1m": "+0.5%",\n    "5m": "+0.7%",\n    "1h": "+0.2%",\n    "degen-audit": "No Honeypot Yes Verified Yes Renounced No Locked 0% Insiders",\n    "taxes-b-s": "0% / 0%",\n    "dev": "--",\n    "": "Buy"\n  }\n]',
        #                          'role': 'user', 'timestamp': 1739527486}], 'user_id': '67ac39d50cef4ea4cf0df45b',
        #         'gpt_id': '67af1045db80df16e4b1880f', 'use_agent': True}
        if len(agent_ids)>0:
            data.update({"team": {"agent_ids": agent_ids}})

        now = datetime.now()
        result = await self._request("POST", "/v2/chat", data=data, timeout=360000)
        print('time comuse ===>', datetime.now() - now)
        return result

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


    async def delete_agent(self, gpt_id: str, agent_id: str):
        """Delete agent from API"""
        data = {
            "gpt_id": gpt_id,
            "agent_id": agent_id
        }
        return await self._request("POST",'/v1/agent/delete', data=data)

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


    agent_configs=[
        {
            "name": "crypto_researcher_agent",
            "description": "Conduct research and analysis if necessary. Can be called multiple times.",
            "system_message": "### Role Description\nYou are a researcher based on the user's instruction to generate a research report. Only proceed when delegated.\n### Workflow\n1. Understand the user instruction，build the request by the request schema of the tool if using the tool \n2. Conduct research by listing the data you get\n3. Generate the research report\n### Input\n* user instruction\n### Output\n1. On top, tell me your execution plan\n2. Pass your report to the next agent",
            "model": "qwen-max",
            "tools": [ "tsdb_query"]
        },
        # {
        #     "name": "crypto_analyst_agent",
        #     "description": "Gather the result from the previous agent, answer the question from the user instruction.",
        #     "system_message": "### Role Description\nYour goal is to provide clear, accurate, and easy-to-understand answers to user inquiries, drawing upon the information provided in the research report.\n### Workflow\n1. Receive the result from the previous agent\n2. Receive the user's question or instruction (user_instruction).\n3. Acknowledge the user's question by restating it to ensure you understand their needs.\n4. Based on the research report, craft a detailed and helpful answer for the user.\n5. Present the answer in a polite, conversational, and easy-to-understand tone, as if engaging in a one-on-one conversation.\n### Input\n* result from the previous agent\n* user_instruction: The user's question or request.\n### Output\nYour reply should follow this format to ensure clarity and a positive user experience:\n* **[Confirmation]:** Begin by restating the user's question or request to confirm your understanding. For example: \"Thank you for your question! I understand you'd like to know...\"\n* **[Answer]:** Provide a direct and concise answer to the user's question, based on the research report.\n* **[Explanation]:** Elaborate on your answer, providing context, reasoning, and any relevant details from the research report. Mention any specific tools, approaches, or methodologies used in the research that support your answer. The goal is to make the answer as clear and helpful as possible.\n* **[Closing]:** End with a polite closing, such as: \"I hope this helps! Please let me know if you have any further questions.\" or \"We're here to assist you further if needed.\"\n\nIf there contains a list of items, Return as a table list in Markdown format.",
        #     "model": "qwen-max"
        # },
        # {
        #     "name": "crypto_execution_agent",
        #     "description": "You are an agent of a crypto transaction execution tool. You do not execute transactions proactively. You only initiate a transaction when the previous agent explicitly provides a crypto transaction execution action for the user or when the user's input contains an explicit and executable transaction instruction.",
        #     "system_message": "### Role Description\nYou are a professional trading agent who calls action tools. You are idle unless you are required to work by user instruction.\n### Workflow\n1. Build the request by the request schema of the tool and execution action by user-provided action trade nlp\n2. Call the tool\n3. Wait for the operation result\n### Input\n* nlp from the user\n### Output\n* action result and format as the response schema of the tool\n* reply including:\nTrade Execution Parameters:\n- Token: SEXCOIN (highest percentage increase)\n- Platform: gmgn.ai (Solana blockchain)\n- Purchase Amount: 0.01 share\n- Current Token Details:\n* Price: Approximately $0.00 (micro-price range)\n* 24h Volume: $182.7K\n* Price Increase: +3,200%",
        #     "model": "qwen-max",
        #     "tools": ["browser_action_nlp"],
        # }
    ]

    fastapi = FastApi()
    # gpt_id = await fastapi.create_gpt()
    # print("gpt_id", gpt_id)
    # gpt_user_id = await fastapi.create_gpt_user()
    # print(gpt_user_id)
    gpt_id = '67b036473feaa412f79ead94'
    gpt_user_id = '67b0733ab80b8cbfc76faf4b'
    # register_result = await fastapi.gpt_register_tool(gpt_id)
    # print("register_result", register_result)
    for c in agent_configs:
        result = await fastapi.create_agent(agent_conf =c, gpt_id=gpt_id)
        print(result)

    # content = "user message: how tokens with marketcap more than $60M,dataframe:67b075dcfd0ea001a3b748f3,user_id:67b0733ab80b8cbfc76faf4b\n response format: if output contain table list, return markdown format"
    # agent_ids = ["67b196403b306b213a6d1cc0", "67b036633feaa412f79ead9a"]
    # chat_result = await fastapi.get_chat_response(user_id=gpt_user_id,content=content,gpt_id=gpt_id, agent_ids=agent_ids)
    # print(chat_result)
    # for c in agent_configs:
    #     result = await fastapi.create_agent(agent_conf=c, gpt_id=gpt_id)
    #     print(result)
    agent_id = '67b176a29bb146c2d80533b9'
    delete_result = await fastapi.delete_agent(gpt_id, agent_id)
    print("delete_result", delete_result)


if __name__ == '__main__':
    asyncio.run(main())
