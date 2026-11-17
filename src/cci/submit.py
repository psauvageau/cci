"""
Submit one document to a Pinecone Assistant.
"""
import logging
import os
import re
from pathlib import Path
from typing import Iterable

import pinecone

_logger = logging.getLogger(__name__)

_KEY_FILE = "pinecone_api_key.txt"



_MCP = "https://prod-1-data.ke.pinecone.io/mcp/assistants/cci"

ASSISTANT_NAME = "cci"

_INVALID_ID_CHARS: re.Pattern[str] = re.compile(r"[^A-Za-z0-9_-]+")
_MAX_ID_LEN: int = 128


def submit_file(file_name:str)->None:
    api_key = _get_api_key()
    pc = pinecone.Pinecone(api_key=_get_api_key())
    print(f"Submitting file {file_name}")

    assistant = find_assistants(pc, ASSISTANT_NAME)
    if not assistant:
        raise RuntimeError(f"Assistant {ASSISTANT_NAME} not found")
    print(f"Found assistant: {assistant}")

    uploaded = upsert_document(pc, Path(file_name), assistant.name)
    print(f"Upserted {file_name} as file {uploaded.id} ({uploaded.status})")



def batch_upsert_files(pc: pinecone.Pinecone, file_names: Iterable[str]) -> None:
    ...

    









def upsert_document(
    pc: pinecone.Pinecone,
    file_path: Path,
    assistant_name: str = ASSISTANT_NAME,
) -> pinecone.AssistantFileModel:
    """
    Upsert a document to a Pinecone assistant.

    The file id is derived from the file name, so submitting the same document
    again replaces the previous version instead of adding a duplicate.
    Blocks until Pinecone has finished processing the file.
    """
    file_id = _file_id(file_path)
    _logger.info("Upserting %s to assistant %s as %s", file_path, assistant_name, file_id)
    return pc.assistants.upload_file(
        assistant_name=assistant_name,
        file_path=str(file_path),
        file_id=file_id,
    )


def _file_id(file_path: Path) -> str:
    """
    Build a Pinecone file id from a file name, e.g. 521584.en.md -> 521584-en.

    File ids must be 1-128 characters: letters, digits, hyphens and underscores.
    """
    file_id = _INVALID_ID_CHARS.sub("-", file_path.stem).strip("-")[:_MAX_ID_LEN]
    if not file_id:
        raise ValueError(f"Cannot derive a Pinecone file id from {file_path.name!r}")
    return file_id

    
    

def find_assistants(pc: pinecone.Pinecone, assistant_name: str) -> pinecone.AssistantModel | None:
    """
    Query the Pinecone API and return all the assistants of the project.

    The paginated listing is fetched in full.
    """
    
    assistants = pc.assistants.list().to_list()
    _logger.debug("Found %d Pinecone assistant(s)", len(assistants))
    for assistant in assistants:
        if assistant.name == assistant_name:
            return assistant
    return None





def _get_api_key()->str:
    path = os.path.join(os.environ["USERPROFILE"], _KEY_FILE)
    with open(path, "r") as f:
        return f.read().strip()
    

