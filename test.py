from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
from browser_use.agent.prompts import SystemPrompt
from dotenv import load_dotenv
load_dotenv()

class MySystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        # Get existing rules from parent class
        existing_rules = super().important_rules()

        # Add your custom rules
        new_rules = """
9. Reference:
- gmgn web url: https://gmgn.ai
"""

        # Make sure to use this pattern otherwise the exiting rules will be lost
        return f'{existing_rules}\n{new_rules}'


async def main():
    agent = Agent(
        task="Go to GMGN, search for 'Trump', buy 100 amount",
        llm=ChatOpenAI(model="gpt-4o"),
        system_prompt_class=MySystemPrompt
    )
    result = await agent.run()
    print(result)

asyncio.run(main())