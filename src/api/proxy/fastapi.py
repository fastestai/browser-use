from typing import Optional, Dict, Any
import aiohttp
import json
import logging
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ApiResponse(BaseModel):
    """API 响应的基础模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class FastApi:
    """外部 API 调用服务"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化外部 API 服务
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥（如果需要）
        """
        self.base_url = 'https://api.fastest.ai'
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """确保 aiohttp session 存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self._get_headers()
            )

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
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
        params: Optional[Dict] = None
    ) -> ApiResponse:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            endpoint: API 端点
            data: 请求体数据
            params: URL 参数
        """
        await self._ensure_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        print("data", data)
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                response_data = await response.json()
                print("response_data",response_data)
                
                if response.status >= 400:
                    return ApiResponse(
                        success=False,
                        error=f"API error: {response.status} - {response_data.get('message', 'Unknown error')}"
                    )
                
                return ApiResponse(
                    success=True,
                    data=response_data
                )
                
        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return ApiResponse(
                success=False,
                error=f"Request failed: {str(e)}"
            )

    async def get_chat_response(self, user_id: str, content: str, gpt_id: str) -> ApiResponse:
        """
        获取聊天响应
        
        Args:
            message: 用户消息
            context: 上下文信息
        """
        data = {
            "user_id": user_id,
            "message": {
                "content": content,
                "role": "user",
                "timestamp": datetime.now().timestamp()
            },
            "gpt_id": gpt_id,
            "use_agent": False
        }
        return await self._request("POST", "/api/v2/chat", data=data)


    async def close(self):
        """关闭 session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()