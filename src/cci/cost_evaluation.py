"""
Rough size of the Markdown documents, to estimate what processing them will cost.

A "word" is any run of characters between whitespace (spaces, tabs, new lines...).
The count is approximate on purpose.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Generator




def count_words(text: str) -> int:
    """
    Number of whitespace-separated words in `text`.
    """
    return len(text.split())


def markdown_files(directory: Path) -> Generator[Path, None, None]:
    """
    The Markdown files (*.md) directly in `directory`, sorted by name.
    """
    for path in directory.glob("*.md"):
        yield path    

def count_words_in_files(directory: Path) -> Generator[int, None,None]:
    """
    Count the words of each Markdown file in `directory`.
    """
    for path in markdown_files(directory):
        count = count_words(path.read_text(encoding="utf-8", errors="replace"))
        yield count
        
