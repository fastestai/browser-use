from typing import List, Optional
from langchain_core.messages import BaseMessage

from browser_use.browser.views import BrowserState, BrowserStateHistory, TabInfo


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

from browser_use.dom.history_tree_processor.view import Coordinates
from browser_use.dom.views import (
	CoordinateSet,
	DOMBaseNode,
	DOMElementNode,
	DOMState,
	DOMTextNode,
	SelectorMap,
	ViewportInfo,
)


class ApiService:
    def __init__(self, task, llm):
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
        self.current_state = Optional[BrowserState]

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        # Get the dynamic action model from controller's registry
        self.ActionModel = self.controller.registry.create_action_model()
        # Create output model with the dynamic actions
        self.AgentOutput = AgentOutput.type_with_custom_actions(self.ActionModel)

    def _create_selector_map(self, element_tree: DOMElementNode) -> SelectorMap:
        selector_map = {}

        def process_node(node: DOMBaseNode):
            if isinstance(node, DOMElementNode):
                if node.highlight_index is not None:
                    selector_map[node.highlight_index] = node

                for child in node.children:
                    process_node(child)

        process_node(element_tree)
        return selector_map

    def _parse_node(
            self,
            node_data: dict,
            parent: Optional[DOMElementNode] = None,
    ) -> Optional[DOMBaseNode]:
        if not node_data:
            return None

        if node_data.get('type') == 'TEXT_NODE':
            text_node = DOMTextNode(
                text=node_data['text'],
                is_visible=node_data['isVisible'],
                parent=parent,
            )
            return text_node

        tag_name = node_data['tagName']

        # Parse coordinates if they exist
        viewport_coordinates = None
        page_coordinates = None
        viewport_info = None

        if 'viewportCoordinates' in node_data:
            viewport_coordinates = CoordinateSet(
                top_left=Coordinates(**node_data['viewportCoordinates']['topLeft']),
                top_right=Coordinates(**node_data['viewportCoordinates']['topRight']),
                bottom_left=Coordinates(**node_data['viewportCoordinates']['bottomLeft']),
                bottom_right=Coordinates(**node_data['viewportCoordinates']['bottomRight']),
                center=Coordinates(**node_data['viewportCoordinates']['center']),
                width=node_data['viewportCoordinates']['width'],
                height=node_data['viewportCoordinates']['height'],
            )

        if 'pageCoordinates' in node_data:
            page_coordinates = CoordinateSet(
                top_left=Coordinates(**node_data['pageCoordinates']['topLeft']),
                top_right=Coordinates(**node_data['pageCoordinates']['topRight']),
                bottom_left=Coordinates(**node_data['pageCoordinates']['bottomLeft']),
                bottom_right=Coordinates(**node_data['pageCoordinates']['bottomRight']),
                center=Coordinates(**node_data['pageCoordinates']['center']),
                width=node_data['pageCoordinates']['width'],
                height=node_data['pageCoordinates']['height'],
            )

        if 'viewport' in node_data:
            viewport_info = ViewportInfo(
                scroll_x=node_data['viewport']['scrollX'],
                scroll_y=node_data['viewport']['scrollY'],
                width=node_data['viewport']['width'],
                height=node_data['viewport']['height'],
            )

        element_node = DOMElementNode(
            tag_name=tag_name,
            xpath=node_data['xpath'],
            attributes=node_data.get('attributes', {}),
            children=[],  # Initialize empty, will fill later
            is_visible=node_data.get('isVisible', False),
            is_interactive=node_data.get('isInteractive', False),
            is_top_element=node_data.get('isTopElement', False),
            highlight_index=node_data.get('highlightIndex'),
            shadow_root=node_data.get('shadowRoot', False),
            parent=parent,
            viewport_coordinates=viewport_coordinates,
            page_coordinates=page_coordinates,
            viewport_info=viewport_info,
        )

        children: list[DOMBaseNode] = []
        for child in node_data.get('children', []):
            if child is not None:
                child_node = self._parse_node(child, parent=element_node)
                if child_node is not None:
                    children.append(child_node)

        element_node.children = children

        return element_node

    def _set_current_state(self, dom_tree: dict, url: str, title: str, tabs: List[TabInfo]):
        element_tree = self._parse_node(node_data=dom_tree)
        selector_map = self._create_selector_map(element_tree)

        self.current_state = BrowserState(
            element_tree=element_tree,
            selector_map=selector_map,
            url=url,
            title=title,
            tabs=tabs
        )

    async def get_next_actions(self, dom_tree: dict, url: str, title: str, tabs: List[TabInfo]):
        self._set_current_state(dom_tree, url, title, tabs)

        self.message_manager.add_state_message(self.current_state)

        input_messages = self.message_manager.get_messages()
        print("input_messages", input_messages)

        structured_llm = self.llm.with_structured_output(self.AgentOutput, include_raw=True,
                                                         method=self.tool_calling_method)
        response: dict[str, Any] = await structured_llm.ainvoke(input_messages)  # type: ignore
        print("reponse", response)
        parsed: AgentOutput | None = response['parsed']
        return response




async def main() -> None:
    api = ApiService(task="Go to GMGN, search for 'Trump', buy 100 amount",
                     llm=ChatOpenAI(model="gpt-4o"))
    await api.get_next_actions()

if __name__ == '__main__':
    asyncio.run(main())
