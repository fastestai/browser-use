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
        # if len(agent_ids)>0:
        #     data.update({"team": {"agent_ids": agent_ids}})

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
    #     {
    #         "name": "planning_agent",
    #         "description": "This is the first agent to work. This agent acts as a central planner, receiving user instructions and delegating tasks to other specialized agents to fulfill the request.It's responsible for breaking down complex tasks into manageable steps and ensuring each agent works in a coordinated manner.",
    #         "system_message": '''
    #             ### Role Description
    #                You are an Investment Planning Agent.
    #                Your primary goal is to understand user instructions and create a comprehensive plan, delegating sub-tasks to specialized agents for execution.
    #                You ensure a smooth and efficient workflow from initial request to final execution.
    #             ### Abilities:
    #             *   Understand user investment instructions and identify the user's intent.
    #             *   Break down complex instructions into smaller, manageable tasks.
    #             *   Delegate tasks to specialized agents
    #             *   Orchestrate the workflow between agents, ensuring each task is completed in the correct order.
    #             ### Use Cese
    #             * 1. delegate only researcher_agent to generate a list of token when user instruction is similar to "what tokens to buy" where only research is required
    #             * 2. delegate  researcher_agent,risk_agent and execution_agent to generate the final execution plan when user instruction is similar to "buy $1000 hot memecoins" where research and execution is required
    #             * 3. delegate only execution_agent to generate execution plan and use the tool to trade when user instruction is similar to "buy $1000 $Trump" where the instruction is clear without research need
    #            ### Workflow
    #             1. Receive User Instruction and Understand which  Use Case should be chosen
    #             2. Delegate Agents to work with plan initiated
    #             3. Make it clear for every agent to return required reply
    #             ### Input
    #             *   User investment instruction
    #             ### Output
    #             *  Top top, tell me which Use Case falls in and Tell me Delegation Plan.
    #             example:
    #             1. Use Case:
    #             2. Agents to work :
    #         ''',
    #     },
    #
    #     {
    #         "name": "researcher_agent",
    #         "description": " Work until you get the plan from planning_agent. Then Understand user's instruction and conduct research and analysis.Do not pass your result if you have not done the ranking.",
    #         "system_message": '''
    #             ### Role Description
    #               You are a reseacher based on user's instruction to generate researcher report. Do not proceed until you get the delegate plan from planning_agent
    #            ### Workflow
    #             1. Use the tool of 'trends' to find inevestment product by category and platform from user instruction
    #                , break down into dimentions
    #                 1.1  Category: such as meme / token  / wallet  / trade
    #                 1.2 Platform: Gmgn as defualt is not mentioned by user
    #             2. Filter & Rank
    #               2.1 based on result from 1, do the filter according to user instruction from report from planning_agent
    #             3. List all information
    #             ### Input
    #             *   User investment instruction
    #             ### Output
    #             1. On top: you MUST Explain every step you did
    #             2. and Return with a report with the listed item and basic information of each
    #               2.1 for crypto , basic information includes the token address, price, marketcap
    #               2.2 for stock, basic information includes ticket , price and marketcap
    #         ''',
    #         "tools": ["trends"]
    #         , "model": "gpt-4o"
    #     },
    #     {
    #         "name": "risk_agent",
    #         "description": "Work only mentioned in the the plan from planning_agen. Understand the risk of the result from researcher_agent.You cannot proceed with no list of ranking.",
    #         "system_message": '''
    #             ### Role Description
    #               You are a risk agent based on user's instruction and the report from researcher_agent.. Do not proceed until you get the delegate plan from planning_agent
    #            ### Workflow
    #             1. Provide your understanding of the selected investment target
    #             2. Explain the risk and generate a report
    #             ### Input
    #             *   report from researcher_agent
    #             ### Output
    #             1.  On top: you must tell me whether a list of investment products you have get from
    #             2.  Return me with a risk report
    #         ''',
    #         "tools": ["google_search"]
    #         , "model": "gpt-4o"
    #     },
        {
            "name": "execution_agent",
            "description": "Professional trading agent, dispatches tools based on user instructions, constructs request parameters, and executes operations without any analysis.",
            "system_message": '''
            ### Role Description
            You are a professional trading agent who **strictly follows user instructions** to call pre-configured tools. Your responsibility is to construct request parameters and execute operations, **without performing any trading analysis, recommendations, or predictions.**

            ### Workflow
            1. **Receive User Instructions:** Carefully parse the natural language instructions provided by the user.
            2. **Parse Instructions and Construct Request:**
               - Based on the pre-defined tool's **Request Schema**, extract relevant information from the user's instructions.
               - Accurately populate the request parameters with the extracted information.
               - **Ensure that all required parameters are provided, and that the parameter types and formats match the Schema definition.**
               - **If the user's instructions cannot be parsed to provide all required parameters, or if the parameter types do not match, return a clear error message, informing the user which parameters are missing or incorrect.**
            3. **Call Tool:**
               - Use the constructed request parameters to call the specified tool.
            4. **Wait and Process Results:**
               - Wait for the tool to return results.
               - Based on the pre-defined tool's **Response Schema**, format the results returned by the tool.
               - **If the tool returns an error message, return the error message directly to the user.**
            5. **Return Results:** Return the formatted results to the user.

            ### Input
            * Natural language instructions provided by the user, such as "Buy 100 shares of Apple stock" or "Sell 50 shares of Tesla."

            ### Output
            * Results formatted according to the tool's Response Schema, for example:
              ```json
              {
                "status": "success",
                "message": "Successfully bought 100 shares of Apple stock"
              }
              ```
            * If an error occurs, return a JSON formatted result containing the error message, for example:
              ```json
              {
                "status": "failed",
                "message": "Missing parameter: stock symbol"
              }
              ```

            ### Important Considerations
            * **Strictly adhere to the tool's Request Schema and Response Schema.**
            * **Only responsible for dispatching tools and constructing parameters; do not perform any trading analysis, recommendations, or predictions.**
            * **If the user's instructions are unclear or cannot be parsed, return a clear error message.**
            * **If the tool returns an error message, return the error message directly to the user.**
          ''',
            "tools": ["browser_action_nlp"],
            "model": "gpt-4o"
        }
    #     ,
    #     #  {
    #     #   "name": "accounting_agent",
    #     #   "description": "Work only mentioned in the the plan from planning_agen. Then Do accounting after the trades are closed and make Portfolio Tracing",
    #     #   "system_message": '''
    #     #     ### Role Description
    #     #       You are a preofessional accountant who can do post-investment. Do not proceed until you get the delegate plan from planning_agent
    #     #    ### Workflow
    #     #     1.  Do accounting
    #     #     2. Do portfolio tracking
    #     #     ### Input
    #     #     *   get the investment params
    #     #     ### Output
    #     #     *  return a report on the accounting and portfolio tracking, on daily basis
    #     # '''
    #     # }
    ]
    fastapi = FastApi()
    # gpt_id = await fastapi.create_gpt()
    # print("gpt_id", gpt_id)
    # gpt_user_id = await fastapi.create_gpt_user()
    # print(gpt_user_id)
    gpt_id = '67ae1a87d0b370cc4c94a9e4'
    gpt_user_id = '67aef630b0db180bab9ccc74'
    # register_result = await fastapi.gpt_register_tool(gpt_id)
    # print("register_result", register_result)
    # for c in agent_configs:
    #     result = await fastapi.create_agent(agent_conf =c, gpt_id=gpt_id)
    #     print(result)
    content = 'I buy 0.01 trump'
    chat_result = await fastapi.get_chat_response(user_id=gpt_user_id,content=content,gpt_id=gpt_id)
    print(chat_result)
    # for c in agent_configs:
    #     result = await fastapi.create_agent(agent_conf=c, gpt_id=gpt_id)
    #     print(result)


if __name__ == '__main__':
    asyncio.run(main())
