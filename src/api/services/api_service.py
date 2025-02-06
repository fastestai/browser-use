from typing import List, Optional
from langchain_core.messages import BaseMessage

import asyncio


from browser_use.agent.message_manager.service import MessageManager
from browser_use.agent.views import (
	ActionResult,
	AgentError,
	AgentHistory,
	AgentHistoryList,
	AgentOutput,
	AgentStepInfo,
)

from pydantic import BaseModel, Field, create_model

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI  # 或其他您使用的LLM

from browser_use.controller.service import Controller
from browser_use.agent.prompts import SystemPrompt


class ApiService:

    def __init__(self, task, llm, action):
        self.llm = llm
        self.task = task
        self.controller = Controller()
        # 初始化可能需要的配置
        self.message_manager = MessageManager(
            llm=llm,
            task=task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=SystemPrompt,

        )
        self.tool_calling_method = 'function_calling'
        self._setup_action_models()

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        # Get the dynamic action model from controller's registry
        self.ActionModel = self.controller.registry.create_action_model()
        # Create output model with the dynamic actions
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)



    async def get_next_actions(self):
        input_messages = self.message_manager.get_messages()
        print("input_messages", input_messages)

        structured_llm = self.llm.with_structured_output(self.AgentOutput, include_raw=True,
                                                         method=self.tool_calling_method)
        response: dict[str, Any] = await structured_llm.ainvoke(input_messages)  # type: ignore
        print("reponse", response)
        parsed: AgentOutput | None = response['parsed']


async def main() -> None:
    api = ApiService(task="Go to GMGN, search for 'Trump', buy 100 amount",
                     llm=ChatOpenAI(model="gpt-4o"))
    await api.get_next_actions()

if __name__ == '__main__':
    asyncio.run(main())
