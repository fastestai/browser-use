from typing import List
import logging
from src.api.model import FileMeta

logger = logging.getLogger(__name__)

def convert_file_context(file_meta: List[dict], content: str, limit: int = 5000) -> str:
    """
    Convert file metadata to a context string format.
    
    Args:
        file_meta: List of file metadata dictionaries containing source_url and content
        content: Original content string
        
    Returns:
        Formatted context string
    """
    file_context = ""
    logger.debug(f"file_meta: {file_meta}")
    
    if not file_meta:
        return file_context
        
    for file in file_meta:
        file_context += f"url: {file['source_url']}\n"
        file_context += f"content: {file['content'][:limit]}\n"
        
    return file_context 