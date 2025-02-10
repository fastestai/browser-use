from typing import AsyncGenerator, Dict, Any
import asyncio

class MonitorService:
    def __init__(self):
        self.agents: Dict[str, Any] = {}

    async def get_agent_updates(self, agent_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """获取代理更新的生成器"""
        if agent_id not in self.agents:
            yield {"status": "error", "message": "Agent not found"}
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

    def register_agent(self, agent_id: str, agent: Any):
        """注册一个新的代理实例"""
        self.agents[agent_id] = agent

    def unregister_agent(self, agent_id: str):
        """注销一个代理实例"""
        if agent_id in self.agents:
            del self.agents[agent_id] 