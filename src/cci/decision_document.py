"""
The document format of a decision: YAML front matter, a title line and the
Markdown body.

    ---
    format_version: 1
    doc_id: tcc-cci-521584-en
    source_url: https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521584/index.do
    ...
    ---

    # Patel v. The King, 2026 TCC 33

    <body>

Every document has the same keys, in the same order. Missing values are
null (or an empty list / mapping). Dates are ISO 8601 strings, so the
metadata can be stored as JSON (e.g. in a vector store) without conversion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yaml

from .decision_metadata import DecisionMetadata

FORMAT_VERSION = 1

_DELIMITER = "---"


def render_document(metadata: DecisionMetadata, body: str, retrieved_at: datetime) -> str:
    """
    Return the complete document of a decision: front matter, title and body.
    `retrieved_at` is when the decision was downloaded.
    """
    front_matter = render_front_matter(front_matter_fields(metadata, retrieved_at))
    return f"{front_matter}\n# {document_title(metadata)}\n\n{body.strip()}\n"


def front_matter_fields(metadata: DecisionMetadata, retrieved_at: datetime) -> dict[str, Any]:
    """
    The front matter of a decision, in document order. Values are JSON compatible.
    """
    return {
        "format_version": FORMAT_VERSION,
        "doc_id": metadata.doc_id,
        "source_url": metadata.source_url,
        "pdf_url": metadata.pdf_url,
        "item_id": metadata.item_id,
        "language": metadata.language,
        "other_languages": dict(metadata.other_languages),
        "court": metadata.court,
        "collection": metadata.collection,
        "case_name": metadata.case_name,
        "neutral_citation": metadata.neutral_citation,
        "decision_date": metadata.decision_date.isoformat() if metadata.decision_date else None,
        "docket_numbers": list(metadata.docket_numbers),
        "judges": list(metadata.judges),
        "subjects": list(metadata.subjects),
        "other_fields": {label: list(values) for label, values in metadata.other_fields.items()},
        "retrieved_at": _utc_iso(retrieved_at),
    }


def render_front_matter(fields: dict[str, Any]) -> str:
    """
    Render fields as a YAML front matter block, keeping their order.
    """
    text = yaml.safe_dump(
        fields,
        sort_keys=False,
        allow_unicode=True,   # Keep "impôt", not "imp\xF4t"
        width=1_000_000,      # Never fold a long value on several lines
    )
    return f"{_DELIMITER}\n{text}{_DELIMITER}\n"


def document_title(metadata: DecisionMetadata) -> str:
    """
    The title line: case name and neutral citation, when they exist.
    """
    parts = [part for part in (metadata.case_name, metadata.neutral_citation) if part]
    return ", ".join(parts) if parts else metadata.doc_id


def read_document(text: str) -> tuple[dict[str, Any], str]:
    """
    Split a document into its front matter fields and the rest (title and body).
    Raise ValueError if the document has no valid front matter.
    """
    first, separator, rest = text.partition(f"\n{_DELIMITER}\n")
    if not first.startswith(f"{_DELIMITER}\n") or not separator:
        raise ValueError("The document has no front matter")
    fields = yaml.safe_load(first.removeprefix(f"{_DELIMITER}\n"))
    if not isinstance(fields, dict):
        raise ValueError("The front matter is not a mapping")
    return fields, rest.lstrip("\n")


def _utc_iso(moment: datetime) -> str:
    """
    Format a datetime as ISO 8601 in UTC, e.g. 2026-11-15T20:46:06Z.
    A naive datetime is taken as UTC.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    utc = moment.astimezone(timezone.utc).replace(microsecond=0)
    return utc.isoformat().replace("+00:00", "Z")
