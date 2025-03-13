import logging
import time
import json
import pandas
import pydash

from src.proxy.aiservice import AIService
from src.utils.file_context import convert_file_context
from src.utils.content import check_valid_json, list_dict_to_markdown
from src.const import RESEARCH_AGENT_ID
from src.utils.util import log_time

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self):
        self.ai_service = AIService()

    @log_time(task="execute_strategy")
    async def execute(self, strategy_output, request, gpt_user_id):
        """Handle research-related operations"""
        task = self._build_context(strategy_output, request)
        logger.debug(f"task:{task}")
        
        response_content = await self._run_agent(task)
        if not check_valid_json(response_content):
            return response_content, None
            
        dataframe = json.loads(response_content)
        dataframe_data = await self._query_tsdb_data(gpt_user_id, dataframe['dataframe_id'])
        token = pydash.get(dataframe_data, '0.token')
        
        if not strategy_output.is_action:
            return self._process_dataframe(dataframe_data), token
        return '', token

    def _build_context(self, strategy_output, request):
        """Build the research task string"""
        task = f'''{strategy_output.research_content}, 
        response format: valid json and json is double quotes, not single quotes.
        output: only json content, not need other content'''
        
        if request.file_meta:
            file_context = convert_file_context(request.file_meta, request.content)
            task = f'base on the context : {file_context}, {task}'
        return task

    @log_time()
    async def _run_agent(self, task):
        """Get and process research response"""
        response = await self.ai_service.run_agent(agent_id=RESEARCH_AGENT_ID, task=task)
        response_content = pydash.get(response.data, 'result')
        logger.debug(f"research result: {response_content}")
        return response_content.replace("```json", "").replace("```", "")

    @log_time()
    async def _query_tsdb_data(self, gpt_user_id, dataframe_id):
        """Query TSDB and get dataframe data"""
        data = await self.ai_service.tsdb_query(user_id=gpt_user_id, dataframe_id=dataframe_id)
        return pydash.get(data, 'data.dataframe.data')

    def _process_dataframe(self, dataframe_data):
        """Process dataframe and convert to markdown"""
        df = pandas.DataFrame(dataframe_data)
        if 'timestamp' in df.columns:
            df = df.drop(columns=['timestamp'])
        df = df.dropna(axis=1, how='any')
        dataframe_list = list(df.to_dict(orient='records'))
        return list_dict_to_markdown(dataframe_list)