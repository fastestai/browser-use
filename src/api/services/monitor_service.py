from typing import AsyncGenerator, Dict, Any
import asyncio
import random

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

class DemoAgent:
    """用于演示的代理类，会定期生成状态更新"""
    def __init__(self):
        self.status_queue = asyncio.Queue()
        self.is_running = True
        # 启动状态更新任务
        asyncio.create_task(self._generate_updates())

    async def _generate_updates(self):
        """生成模拟的状态更新"""
        while self.is_running:
            # 模拟不同类型的状态更新
            status_types = ['running', 'processing', 'waiting']
            status_update = {
                'status': random.choice(status_types),
                'timestamp': asyncio.get_running_loop().time(),
                'memory_usage': random.randint(50, 200),
                'cpu_usage': random.uniform(0, 100)
            }
            
            await self.status_queue.put(status_update)
            # 每1-3秒生成一次更新
            await asyncio.sleep(random.uniform(1, 3))

    def stop(self):
        """停止生成状态更新"""
        self.is_running = False 