"""
Submit one document to a Pinecone Assistant.
"""
import logging
import os
import re
from pathlib import Path
from typing import Generator, Iterable, Optional
import time

import pinecone

_logger = logging.getLogger(__name__)

_KEY_FILE = "pinecone_dan_api_key.txt"

_MCP = "https://prod-1-data.ke.pinecone.io/mcp/assistants/cci"

_LUDICROUSLY_HIGH_MAX_FILES = 10000000

ASSISTANT_NAME = "cci"

_INVALID_ID_CHARS: re.Pattern[str] = re.compile(r"[^A-Za-z0-9_-]+")
_MAX_ID_LEN: int = 128


def submit_file(file_name:str)->None:    
    pc = pinecone.Pinecone(api_key=_get_api_key())
    _logger.info(f"Submitting file {file_name}")

    assistant = _find_assistants(pc, ASSISTANT_NAME)
    if not assistant:
        raise RuntimeError(f"Assistant {ASSISTANT_NAME} not found")
    
    path = Path(file_name)
    if path.is_dir():
        batch_upload_files(pc, assistant.name, _get_md_files(path), max_files=100)
    else:
        upload_file(pc, path, assistant.name)
    


class Timer:
    def __init__(self)->None:
        self.start_time = time.time()
        self.file_count:int = 0

    def increment_file_count(self)->None:
        self.file_count += 1
        elapsed_time = time.time() - self.start_time
        _logger.info("Processed %d file(s). Average: %.2f seconds per file", self.file_count, elapsed_time / self.file_count if self.file_count > 0 else 0)
 

    



def batch_upload_files(pc: pinecone.Pinecone, 
                       assistant_name: str, 
                       files: Iterable[Path], 
                       max_files: int = _LUDICROUSLY_HIGH_MAX_FILES) -> None:
    """
    Upload the files that the assistant does not have yet.

    The ids already in the assistant are listed once at the start, so each file
    is checked against that set instead of with one request per file.
    """
    existing_ids = {file.id for file in list_files(pc, assistant_name)}
    _logger.info("Assistant %s already has %d file(s)", assistant_name, len(existing_ids))

    count = len(existing_ids)
    _logger.info("Starting batch upload. Current count: %d", count)

    timer = Timer()
    for file in files:
        file_id = _file_id(file)
        if file_id in existing_ids:
            _logger.debug("Skipping %s: %s is already in assistant %s", file, file_id, assistant_name)
            continue

        _logger.info("Uploading file: %s", file)
        # Already checked against the set: overwrite=True avoids checking again.
        upload_file(pc, file, assistant_name, overwrite=True)
        existing_ids.add(file_id)
        timer.increment_file_count()
        count += 1
        if count >= max_files:
            _logger.info("Reached max_files limit: %d", max_files)
            break

    




def upload_file(
    pc: pinecone.Pinecone,
    file_path: Path,
    assistant_name: str = ASSISTANT_NAME,
    overwrite:bool = False
) -> Optional[pinecone.AssistantFileModel]:
    """
    Upsert a document to a Pinecone assistant.

    The file id is derived from the file name, so submitting the same document
    again replaces the previous version instead of adding a duplicate.
    Blocks until Pinecone has finished processing the file.
    """
    if not overwrite:
        if check_file_exists(pc, _file_id(file_path), assistant_name):
            _logger.debug("File %s already exists in assistant %s", _file_id(file_path), assistant_name)
            return None


    file_id = _file_id(file_path)
    _logger.info("Uploading %s to assistant %s as %s", file_path, assistant_name, file_id)
    return pc.assistants.upload_file(
        assistant_name=assistant_name,
        file_path=str(file_path),
        file_id=file_id,
    )


def check_file_exists(
    pc: pinecone.Pinecone,
    file_id: str,
    assistant_name: str = ASSISTANT_NAME,
) -> bool:
    """
    Return True if the assistant already has a file with this id, e.g. 521584-en.

    Any file found counts, whatever its status ("Processing", "Available",
    "ProcessingFailed"...).
    """
    try:
        file = pc.assistants.describe_file(assistant_name=assistant_name, file_id=file_id)
    except pinecone.NotFoundError:
        _logger.debug("File %s not found in assistant %s", file_id, assistant_name)
        return False
    _logger.debug("File %s found in assistant %s (%s)", file_id, assistant_name, file.status)
    return True


def list_files(
    pc: pinecone.Pinecone,
    assistant_name: str = ASSISTANT_NAME,
) -> list[pinecone.AssistantFileModel]:
    """
    Return all the files of the assistant (id, name, status...).

    The paginated listing is fetched in full. Pinecone leaves out a
    "ProcessingFailed" file once it is old enough; check_file_exists still finds it.
    """
    files = pc.assistants.list_files(assistant_name=assistant_name).to_list()
    _logger.debug("Found %d file(s) in assistant %s", len(files), assistant_name)
    return files


def _file_id(file_path: Path) -> str:
    """
    Build a Pinecone file id from a file name, e.g. 521584.en.md -> 521584-en.

    File ids must be 1-128 characters: letters, digits, hyphens and underscores.
    """
    file_id = _INVALID_ID_CHARS.sub("-", file_path.stem).strip("-")[:_MAX_ID_LEN]
    if not file_id:
        raise ValueError(f"Cannot derive a Pinecone file id from {file_path.name!r}")
    return file_id

    
    

def _find_assistants(pc: pinecone.Pinecone, assistant_name: str) -> pinecone.AssistantModel | None:
    """
    Query the Pinecone API and return all the assistants of the project.

    The paginated listing is fetched in full.
    """
    
    assistants = pc.assistants.list().to_list()
    _logger.debug("Found %d Pinecone assistant(s)", len(assistants))
    for assistant in assistants:
        if assistant.name == assistant_name:
            _logger.debug(f"Found assistant: {assistant}")
            return assistant
    return None


def _get_md_files(path:Path) -> Generator[Path, None, None]:
    for p in path.glob("*.md"):
        if p.is_file():
            yield p


def _get_api_key()->str:
    path = os.path.join(os.environ["USERPROFILE"], _KEY_FILE)
    with open(path, "r") as f:
        return f.read().strip()
    

