from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing import Any, Type

async def call_llm(system_content: str, human_content: str, schema: Type[BaseModel]) -> Any:
    llm = ChatOpenAI(model_name="gpt-4o")
    system_message = SystemMessage(content=system_content)
    human_message = HumanMessage(content=human_content)
    msg = [system_message, human_message]
    structured_llm = llm.with_structured_output(schema=schema, include_raw=True, method="function_calling")
    result = await structured_llm.ainvoke(msg)
    return result