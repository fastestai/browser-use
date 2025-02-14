from typing import AsyncGenerator, Dict, Any
import asyncio
import random

class BaseMonitorAgent:
    """Base monitoring agent class"""
    def __init__(self):
        self.status_queue = asyncio.Queue()

    def get_status_queue_size(self):
        return self.status_queue.qsize()


class BrowserPluginMonitorAgent(BaseMonitorAgent):
    """Browser plugin monitoring agent implementation"""
    def __init__(self, browser_plugin_id: str, gpt_user_id: str):
        super().__init__()
        self.gpt_user_id = gpt_user_id
        self.browser_plugin_id = browser_plugin_id
        # self.is_running = True
        # 启动状态更新任务
        # asyncio.create_task(self._generate_updates())

    def set_gpt_user_id(self, gpt_user_id: str):
        self.gpt_user_id = gpt_user_id

    def get_gpt_user_id(self):
        """Get the GPT user ID associated with this agent"""
        return self.gpt_user_id

    # async def _generate_updates(self):
    #     """生成模拟的状态更新"""
    #     while self.is_running:
    #         # 模拟不同类型的状态更新
    #         status_types = ['running', 'processing', 'waiting']
    #         status_update = {
    #             'status': random.choice(status_types),
    #             'timestamp': asyncio.get_running_loop().time(),
    #             'memory_usage': random.randint(50, 200),
    #             'cpu_usage': random.uniform(0, 100)
    #         }
    #
    #         await self.status_queue.put(status_update)
    #         # 每1-3秒生成一次更新
    #         await asyncio.sleep(random.uniform(1, 3))

    # def stop(self):
    #     """停止生成状态更新"""
    #     self.is_running = False




class MonitorService:
    """Service for managing monitoring agents"""
    def __init__(self):
        self.agents: Dict[str, BrowserPluginMonitorAgent] = {}

    def get_agents(self) -> Dict[str, BrowserPluginMonitorAgent]:
        """Get all registered agents"""
        return self.agents

    async def get_agent_updates(self, agent_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Get updates generator for specific agent
        
        Args:
            agent_id: Agent identifier
            
        Yields:
            Dict containing agent status updates
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        while True:
            try:
                # 从代理的状态队列中获取更新
                status = await agent.status_queue.get()
                yield status
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield {"status": "error", "message": str(e)}
                break

    def register_agent(self, agent_id: str, agent: BrowserPluginMonitorAgent):
        """注册一个新的代理实例"""
        self.agents[agent_id] = agent

    def unregister_agent(self, agent_id: str):
        """注销一个代理实例"""
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_agent(self, agent_id: str) -> BrowserPluginMonitorAgent:
        """
        Get agent instance by ID
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            BrowserPluginMonitorAgent: Agent instance
            
        Raises:
            KeyError: When agent ID doesn't exist
        """
        if agent_id not in self.agents:
            raise KeyError(f"Agent not found: {agent_id}")
        return self.agents[agent_id]