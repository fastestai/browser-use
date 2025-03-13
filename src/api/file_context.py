from src.api.model import FileMeta

def convert_file_context(file_meta: list[FileMeta], content: str) -> str | None:
    file_context = ""
    for file in file_meta:
        file_context += f"url: {file.source_url}\n"
        # todo this content is temporary, need to be replaced by the real content by fetch from the file_url or by file_id
        file_context += f"content: {file.content}\n"
    return file_context
