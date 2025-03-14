from typing import List
import logging
from bs4 import BeautifulSoup
# from src.api.model import FileMeta

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
        # Convert HTML to plain text before truncating
        html_content = file['content']
        soup = BeautifulSoup(html_content, 'html.parser')
        plain_text = soup.get_text(separator=' ', strip=True)
        file_context += f"content: {plain_text[:limit]}\n"
        
    return file_context 