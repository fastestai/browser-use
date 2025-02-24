import logging

from typing import List, Optional

from browser_use.browser.views import BrowserState, TabInfo
from browser_use.agent.message_manager.service import MessageManager, MessageManagerSettings
from browser_use.agent.service import log_response
from browser_use.agent.views import (
    AgentOutput, ActionResult, AgentSettings, AgentState,
)
from browser_use.agent.prompts import SystemPrompt
from src.controller.service import Controller
from browser_use.dom.history_tree_processor.view import Coordinates
from browser_use.dom.views import (
	CoordinateSet,
	DOMBaseNode,
	DOMElementNode,
	DOMTextNode,
	SelectorMap,
	ViewportInfo,
)

from src.action.models import MySystemPrompt


logger = logging.getLogger(__name__)


class ActionAgentService:
    def __init__(self, task, llm, controller=Controller(), override_system_message = None, extend_system_message = None, sensitive_data = None):
        self.llm = llm
        self.task = task
        self.controller = controller
        self.settings = AgentSettings()
        self.available_actions = self.controller.registry.get_prompt_description()
        self.state = AgentState()
        # 初始化可能需要的配置
        self.message_manager = MessageManager(
            task=task,
            system_message=SystemPrompt(
                action_description=self.available_actions,
                max_actions_per_step=self.settings.max_actions_per_step,
                override_system_message=override_system_message,
                extend_system_message=extend_system_message,
            ).get_system_message(),
            settings=MessageManagerSettings(
                max_input_tokens=self.settings.max_input_tokens,
                include_attributes=self.settings.include_attributes,
                message_context=self.settings.message_context,
                sensitive_data=sensitive_data,
                available_file_paths=self.settings.available_file_paths,
            ),
            state=self.state.message_manager_state,
        )
        self.tool_calling_method = 'function_calling'
        self._setup_action_models()
        self.current_state = Optional[BrowserState]
        self.latest_result: Optional[List[ActionResult]] = None

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

        self.message_manager.add_state_message(self.current_state, self.latest_result)

        input_messages = self.message_manager.get_messages()

        structured_llm = self.llm.with_structured_output(self.AgentOutput, include_raw=True,
                                                         method=self.tool_calling_method)
        response: dict[str, Any] = await structured_llm.ainvoke(input_messages)  # type: ignore
        parsed: AgentOutput | None = response['parsed']
        logger.info(f"Received parsed data: {parsed}")
        log_response(parsed)
        return response

    async def set_action_result(self, result: ActionResult):
        self.latest_result = [result]
        return self.latest_result

    def log_response(self, response: AgentOutput) -> None:

        if 'Success' in response.current_state.evaluation_previous_goal:
            emoji = '👍'
        elif 'Failed' in response.current_state.evaluation_previous_goal:
            emoji = '⚠'
        else:
            emoji = '🤷'
        logger.debug(f'🤖 {emoji} Page summary: {response.current_state.page_summary}')
        logger.info(f'{emoji} Eval: {response.current_state.evaluation_previous_goal}')
        logger.info(f'🧠 Memory: {response.current_state.memory}')
        logger.info(f'🎯 Next goal: {response.current_state.next_goal}')
        for i, action in enumerate(response.action):
            logger.info(f'🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}')

