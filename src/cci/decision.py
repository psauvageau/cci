"""
Get the text of one Tax Court of Canada decision.

A decision page (e.g. .../decisions/en/item/521584/index.do) shows the
decision in the iframe version of the page (``?iframe=true``), inside
``<div class="documentcontent">``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from ._http import get_html

_CONTENT_CLASS = "documentcontent"

# Tags that start a new paragraph in the text.
_BLOCK_TAGS = frozenset(
    {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "ul", "tr", "table",
     "blockquote"}
)
# Tags whose content is not part of the text.
_SKIP_TAGS = frozenset({"script", "style"})


def get_decision(url: str) -> str:
    """
    Return the text of the decision at the given URL.
    """
    html = fetch_decision_html(url)
    return extract_decision_text(html)


def fetch_decision_html(url: str) -> str:
    """
    Download the HTML that contains the decision.
    """
    return get_html(url, params={"iframe": "true"})


def extract_decision_text(html: str) -> str:
    """
    Extract the decision as plain text: one paragraph per block,
    separated by a blank line. Raise ValueError if there is no decision.
    """
    extractor = _DecisionTextExtractor()
    extractor.feed(html)
    extractor.close()
    if not extractor.found:
        raise ValueError("No decision content found in the page")
    return _normalize_text(extractor.text())


def _normalize_text(text: str) -> str:
    """
    Trim each line and keep at most one blank line between paragraphs.
    """
    lines = [line.strip() for line in text.splitlines()]
    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip() + "\n"


@dataclass
class _OpenList:
    """
    An <ol> or <ul> being parsed, and the number of its next item.
    """
    ordered: bool
    style: str = "1"
    next_number: int = 1

    def next_marker(self) -> str:
        """
        Return the marker of the next item ("1.", "b.", "iv.", "-") and advance.
        """
        number = self.next_number
        self.next_number += 1
        if not self.ordered:
            return "-"
        return f"{_format_list_number(number, self.style)}."


class _DecisionTextExtractor(HTMLParser):
    """
    Collect the text inside <div class="documentcontent">.
    """

    def __init__(self) -> None:
        super().__init__()
        self.found = False
        self._div_depth = 0   # > 0 while inside the decision content
        self._skip_depth = 0  # > 0 while inside <script> or <style>
        self._parts: list[str] = []
        self._lists: list[_OpenList] = []       # Lists being parsed, innermost last
        self._pending_marker: str | None = None  # Marker waiting for its item's text

    def text(self) -> str:
        return "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._div_depth == 0:
            if tag == "div" and _has_class(attrs, _CONTENT_CLASS):
                self.found = True
                self._div_depth = 1
            return

        if tag == "div":
            self._div_depth += 1
        self._start_list_tag(tag, attrs)
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in _BLOCK_TAGS:
            self._parts.append("\n\n")
        elif tag == "br":
            self._parts.append("\n")
        elif tag in ("td", "th"):
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._div_depth == 0:
            return

        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in ("ol", "ul") and self._lists:
            self._lists.pop()
            self._pending_marker = None  # An empty last item has no text to mark
        if tag in _BLOCK_TAGS:
            self._parts.append("\n\n")
        if tag == "div":
            self._div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._div_depth > 0 and self._skip_depth == 0:
            # The marker goes right before the item's first text, so it stays
            # on the same line even when the item starts with a <p>.
            if self._pending_marker is not None and data.strip():
                self._parts.append(self._pending_marker + " ")
                self._pending_marker = None
            # Line breaks in the HTML source are not line breaks in the text.
            self._parts.append(re.sub(r"\s+", " ", data))

    def _start_list_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Track <ol>/<ul> nesting and prepare the marker of each <li>.
        """
        attributes = dict(attrs)
        if tag == "ol":
            self._lists.append(_OpenList(
                ordered=True,
                style=attributes.get("type") or "1",
                next_number=_parse_start(attributes.get("start")),
            ))
        elif tag == "ul":
            self._lists.append(_OpenList(ordered=False))
        elif tag == "li" and self._lists:
            self._pending_marker = self._lists[-1].next_marker()


def _parse_start(value: str | None) -> int:
    """
    Parse the start attribute of an <ol>; default to 1 when missing or invalid.
    """
    try:
        return int(value) if value is not None else 1
    except ValueError:
        return 1


_ROMAN_NUMERALS = (
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
    (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
)


def _format_list_number(number: int, style: str) -> str:
    """
    Format a list item number following the HTML <ol type="..."> styles.
    """
    if style in ("a", "A") and 1 <= number <= 26:
        letter = chr(ord("a") + number - 1)
        return letter.upper() if style == "A" else letter
    if style in ("i", "I") and number >= 1:
        roman = _to_roman(number)
        return roman.upper() if style == "I" else roman
    return str(number)


def _to_roman(number: int) -> str:
    parts: list[str] = []
    for value, numeral in _ROMAN_NUMERALS:
        while number >= value:
            parts.append(numeral)
            number -= value
    return "".join(parts)


def _has_class(attrs: list[tuple[str, str | None]], name: str) -> bool:
    classes = (dict(attrs).get("class") or "").split()
    return name in classes
