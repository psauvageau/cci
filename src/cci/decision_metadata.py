"""
Parse the metadata of a Tax Court of Canada decision page.

The metadata is read from the iframe version of a decision page:

- ``<link rel="canonical">``: the canonical URL of the decision
- ``<h3 class="title">``: the case name
- a table of ``<td class="label">`` / ``<td class="metadata">`` rows
  (labels in English or French, values separated by ``<br>``)
- ``<div class="documents">``: the link to the PDF version
- ``<div id="decisia-alternate-url-value-<lang>">``: the other language versions
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

_logger = logging.getLogger(__name__)

COURT = "Tax Court of Canada"

# Path of a decision page: /<client>/decisions/<lang>/item/<id>/index.do
_DECISION_PATH = re.compile(r"/decisions/(?P<lang>[a-z]{2})/item/(?P<id>\d+)/index\.do$")

_ALTERNATE_URL_ID = re.compile(r"^decisia-alternate-url-value-(?P<lang>[a-z]{2})$")

# Metadata table labels (normalized, English and French) -> DecisionMetadata field.
_LABEL_FIELDS: dict[str, str] = {
    "court (s) database": "collection",
    "base de données - cour (s)": "collection",
    "date": "decision_date",
    "neutral citation": "neutral_citation",
    "référence neutre": "neutral_citation",
    "file number": "docket_numbers",
    "file numbers": "docket_numbers",
    "numéro de dossier": "docket_numbers",
    "numéros de dossier": "docket_numbers",
    "judges and taxing officers": "judges",
    "juges et officiers taxateurs": "judges",
    "subject": "subjects",
    "subjects": "subjects",
    "sujet": "subjects",
    "sujets": "subjects",
}


@dataclass
class DecisionMetadata:
    """
    Metadata of one decision, in one language. Fields missing from the
    page are None (single values) or empty (lists).
    """
    source_url: str
    item_id: int
    language: str
    case_name: str | None = None
    collection: str | None = None
    decision_date: date | None = None
    neutral_citation: str | None = None
    docket_numbers: list[str] = field(default_factory=list)
    judges: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    pdf_url: str | None = None
    other_languages: dict[str, str] = field(default_factory=dict)
    court: str = COURT
    # Metadata rows with a label we don't know: label -> values. Kept so nothing is lost.
    other_fields: dict[str, list[str]] = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        """
        Stable identifier of this decision in this language.
        """
        return f"tcc-cci-{self.item_id}-{self.language}"


def parse_metadata(html: str, url: str) -> DecisionMetadata:
    """
    Parse the metadata of the decision page `html`, downloaded from `url`.
    Raise ValueError if the page is not a decision page.
    """
    page = _MetadataCollector.collect(html)
    if page.case_name is None and not page.rows:
        raise ValueError(f"No decision metadata found in the page {url}")

    source_url = canonical_url(urljoin(url, page.canonical_url or url))
    item_id, language = parse_decision_url(source_url)

    metadata = DecisionMetadata(
        source_url=source_url,
        item_id=item_id,
        language=language,
        case_name=page.case_name,
        pdf_url=urljoin(source_url, page.pdf_href) if page.pdf_href else None,
        other_languages={
            lang: canonical_url(urljoin(source_url, href))
            for lang, href in page.alternate_hrefs.items()
        },
    )
    for label, values in page.rows:
        _set_field(metadata, label, values)
    return metadata


def parse_decision_url(url: str) -> tuple[int, str]:
    """
    Return the (item id, language) of a decision URL.
    Raise ValueError if the URL is not a decision URL.
    """
    match = _DECISION_PATH.search(urlsplit(url).path)
    if match is None:
        raise ValueError(f"Not a decision URL: {url}")
    return int(match["id"]), match["lang"]


def canonical_url(url: str) -> str:
    """
    Remove the query and fragment of a URL (e.g. ?iframe=true, ?alternatelocale=en).
    """
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _set_field(metadata: DecisionMetadata, label: str, values: list[str]) -> None:
    """
    Store the values of one metadata row in the matching field.
    """
    field_name = _LABEL_FIELDS.get(_normalize_label(label))
    if field_name is None:
        _logger.warning("Unknown metadata label %r in %s", label, metadata.source_url)
        metadata.other_fields[label] = values
    elif field_name == "collection":
        metadata.collection = _first(values)
    elif field_name == "decision_date":
        metadata.decision_date = _parse_date(_first(values), metadata.source_url)
    elif field_name == "neutral_citation":
        metadata.neutral_citation = _first(values)
    elif field_name == "docket_numbers":
        metadata.docket_numbers = _split_commas(values)
    elif field_name == "judges":
        metadata.judges = values
    elif field_name == "subjects":
        metadata.subjects = values


def _normalize_label(label: str) -> str:
    """
    Lowercase, collapse whitespace and use a plain hyphen for all dashes.
    """
    label = re.sub(r"[‐-―]", "-", label)
    return " ".join(label.split()).casefold()


def _first(values: list[str]) -> str | None:
    return values[0] if values else None


def _split_commas(values: list[str]) -> list[str]:
    return [part.strip() for value in values for part in value.split(",") if part.strip()]


def _parse_date(value: str | None, source_url: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        _logger.warning("Invalid decision date %r in %s", value, source_url)
        return None


class _MetadataCollector(HTMLParser):
    """
    Collect the raw metadata of a decision page.
    """

    def __init__(self) -> None:
        super().__init__()
        self.canonical_url: str | None = None
        self.case_name: str | None = None
        self.rows: list[tuple[str, list[str]]] = []     # (label, values) in page order
        self.pdf_href: str | None = None
        self.alternate_hrefs: dict[str, str] = {}       # language -> href

        self._capture: str | None = None   # What the current text belongs to
        self._text: list[str] = []         # Text of the current title / label / value
        self._label: str | None = None     # Label of the current row
        self._values: list[str] = []       # Values of the current row
        self._in_documents = False

    @classmethod
    def collect(cls, html: str) -> _MetadataCollector:
        parser = cls()
        parser.feed(html)
        parser.close()
        return parser

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()

        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical_url = attributes.get("href")
        elif tag == "h3" and "title" in classes and self.case_name is None:
            self._start_capture("title")
        elif tag == "td" and "label" in classes:
            self._start_capture("label")
        elif tag == "td" and "metadata" in classes:
            if self._capture == "label":  # In case the label cell is not closed
                self._label = self._captured_text()
            self._start_capture("value")
        elif tag == "br" and self._capture == "value":
            self._end_value()
        elif tag == "div" and "documents" in classes:
            self._in_documents = True
        elif tag == "a" and self._in_documents and self.pdf_href is None:
            self.pdf_href = attributes.get("href")
        elif tag == "div":
            match = _ALTERNATE_URL_ID.match(attributes.get("id") or "")
            if match:
                self._start_capture("alternate:" + match["lang"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._capture == "title":
            self.case_name = self._captured_text() or None
            self._capture = None
        elif tag in ("td", "tr") and self._capture == "label":
            self._label = self._captured_text()
            self._capture = None
        elif tag in ("td", "tr") and self._capture == "value":
            self._end_value()
            self._capture = None
        elif tag == "div" and self._capture and self._capture.startswith("alternate:"):
            self.alternate_hrefs[self._capture.removeprefix("alternate:")] = self._captured_text()
            self._capture = None
        elif tag == "div":
            self._in_documents = False

        # The <td> cells of the metadata table are not closed: a row ends with </tr>.
        if tag == "tr" and self._label is not None:
            self.rows.append((self._label, self._values))
            self._label = None
            self._values = []

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._text.append(data)

    def _start_capture(self, what: str) -> None:
        self._capture = what
        self._text = []

    def _captured_text(self) -> str:
        return " ".join("".join(self._text).split())

    def _end_value(self) -> None:
        """
        End one value of the current row (values are separated by <br>).
        """
        value = self._captured_text()
        if value:
            self._values.append(value)
        self._text = []
