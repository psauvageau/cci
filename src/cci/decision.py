"""
Get one Tax Court of Canada decision as a Markdown document with its metadata.

A decision page (e.g. .../decisions/en/item/521584/index.do) shows the
decision in the iframe version of the page (``?iframe=true``).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ._http import get_html
from .decision_document import render_document
from .decision_markdown import html_to_markdown
from .decision_metadata import parse_metadata


def get_decision(url: str) -> str:
    """
    Return the decision at the given URL, as a Markdown document
    with its metadata in YAML front matter.
    """
    html = fetch_decision_html(url)
    return decision_document(html, url, retrieved_at=datetime.now(timezone.utc))


def fetch_decision_html(url: str) -> str:
    """
    Download the HTML that contains the decision.
    """
    return get_html(url, params={"iframe": "true"})


def decision_document(html: str, url: str, retrieved_at: datetime) -> str:
    """
    Build the document of a decision from its page, downloaded from `url`
    at `retrieved_at`.
    """
    metadata = parse_metadata(html, url)
    body = html_to_markdown(html)
    return render_document(metadata, body, retrieved_at)
