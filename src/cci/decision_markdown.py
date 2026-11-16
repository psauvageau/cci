"""
Convert the HTML of a Tax Court of Canada decision to Markdown for an LLM.

Only the structure is kept: headings, paragraphs, lists, table rows and
footnotes. Styling (bold, italics, fonts...) is dropped.

The decision is inside ``<div class="documentcontent">``:

- ``<h1>``..``<h5>`` become ``##``..``######`` (``#`` is left for the document title)
- footnote references are links to ``#_ftnN``; they become ``[^N]``
- footnotes are ``<div id="ftnN">`` blocks; they become ``[^N]: ...``
  definitions in a final ``## Footnotes`` section
- table rows become one line, with the non-empty cells joined by `` | ``
- list items are numbered following the ``<ol type="..." start="...">`` attributes
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

_CONTENT_CLASS = "documentcontent"

FOOTNOTES_HEADING = "## Footnotes"

# Tags that start a new paragraph.
_BLOCK_TAGS = frozenset(
    {"p", "div", "li", "ol", "ul", "table", "blockquote", "pre", "hr"}
)
# Tags whose content is not part of the text.
_SKIP_TAGS = frozenset({"script", "style"})
_HEADING_TAG = re.compile(r"^h([1-6])$")
_EMPTY_HEADING = re.compile(r"^#+$")

# Footnotes as exported by Word: reference <a href="#_ftn5">, back link
# <a href="#_ftnref5"> and footnote block <div id="ftn5">.
_FOOTNOTE_REF_HREF = re.compile(r"^#_?ftn(\d+)$")
_FOOTNOTE_BACK_HREF = re.compile(r"^#_?ftnref(\d+)$")
_FOOTNOTE_ID = re.compile(r"^_?ftn(\d+)$")

# Placeholder for one level of list indentation. Lines are trimmed while the
# text is normalized, so the indentation is only added at the very end.
_INDENT_MARK = "\x01"
_INDENT = "    "

# Placeholder for a paragraph or line break inside a table cell. A cell is
# written on one line, so its paragraphs are joined with _CELL_SEPARATOR.
_CELL_BREAK_MARK = "\x02"
_CELL_SEPARATOR = "; "


def html_to_markdown(html: str) -> str:
    """
    Convert the decision in `html` to Markdown.
    Raise ValueError if the page has no decision content.
    """
    converter = _MarkdownConverter()
    converter.feed(html)
    converter.close()
    if not converter.found:
        raise ValueError("No decision content found in the page")

    markdown = normalize_blocks(converter.body_text())
    if converter.footnotes:
        markdown += "\n\n" + render_footnotes(converter.footnotes)
    return markdown + "\n"


def render_footnotes(footnotes: dict[int, str]) -> str:
    """
    Render footnote definitions. The paragraphs after the first one are
    indented so they stay part of the footnote.
    """
    definitions = []
    for number, text in footnotes.items():
        first, *others = text.split("\n\n")
        lines = [f"[^{number}]: {first}"] + [_INDENT + other for other in others]
        definitions.append("\n\n".join(lines))
    return FOOTNOTES_HEADING + "\n\n" + "\n\n".join(definitions)


def normalize_blocks(text: str) -> str:
    """
    Trim each line, keep at most one blank line between blocks
    and expand the list indentation marks.
    """
    lines = [line.strip() for line in text.splitlines()]
    lines = ["" if _EMPTY_HEADING.match(line) else line for line in lines]
    joined = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return joined.replace(_INDENT_MARK, _INDENT)


def _normalize_cell(text: str) -> str:
    """
    Put the text of a table cell on one line, its paragraphs joined by "; ".
    """
    text = text.replace(_INDENT_MARK, "")
    paragraphs = (" ".join(part.split()) for part in text.split(_CELL_BREAK_MARK))
    return _CELL_SEPARATOR.join(paragraph for paragraph in paragraphs if paragraph)


@dataclass
class _OpenList:
    """
    An <ol> or <ul> being converted, and the number of its next item.
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
        return f"{format_list_number(number, self.style)}."


@dataclass
class _OpenRow:
    """
    A table row being converted.
    """
    cells: list[str] = field(default_factory=list)
    cell_open: bool = False


class _MarkdownConverter(HTMLParser):
    """
    Convert the content of <div class="documentcontent"> to Markdown.

    Text is written to a stack of buffers: the bottom one is the body,
    the others collect a table cell or a footnote until it is complete.
    """

    def __init__(self) -> None:
        super().__init__()
        self.found = False
        self.footnotes: dict[int, str] = {}   # Number -> text, in page order

        self._div_depth = 0       # > 0 while inside the decision content
        self._skip_depth = 0      # > 0 while inside <script> or <style>
        self._buffers: list[list[str]] = [[]]
        self._lists: list[_OpenList] = []            # Open lists, innermost last
        self._pending_marker: str | None = None      # List marker waiting for its item's text
        self._tables: list[_OpenRow | None] = []     # Current row of each open table
        self._heading = False
        self._footnote: tuple[int, int] | None = None  # (number, div depth) of the open footnote
        self._hide_anchor_text = False

    def body_text(self) -> str:
        return "".join(self._buffers[0])

    # --- HTMLParser callbacks -------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self._div_depth == 0:
            if tag == "div" and _CONTENT_CLASS in (attributes.get("class") or "").split():
                self.found = True
                self._div_depth = 1
            return
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if self._skip_depth > 0:
            return

        if tag == "div":
            self._div_depth += 1
            self._start_footnote(attributes.get("id"))
        elif tag == "a":
            self._start_anchor(attributes.get("href"))
        elif tag == "ol":
            self._lists.append(_OpenList(
                ordered=True,
                style=attributes.get("type") or "1",
                next_number=parse_list_start(attributes.get("start")),
            ))
        elif tag == "ul":
            self._lists.append(_OpenList(ordered=False))
        elif tag == "li" and self._lists:
            indent = _INDENT_MARK * (len(self._lists) - 1)
            self._pending_marker = indent + self._lists[-1].next_marker()
        elif tag == "table":
            self._tables.append(None)
        elif tag == "tr":
            self._start_row()
        elif tag in ("td", "th"):
            self._start_cell()
        elif tag == "br":
            self._write(self._line_break("\n"))
        elif (match := _HEADING_TAG.match(tag)) and not self._single_line():
            level = min(int(match[1]) + 1, 6)
            self._write("\n\n" + "#" * level + " ")
            self._heading = True

        if tag in _BLOCK_TAGS:
            self._write_block_break()

    def handle_endtag(self, tag: str) -> None:
        if self._div_depth == 0:
            return
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth > 0:
            return

        if tag == "div":
            self._end_footnote()
            self._div_depth -= 1
        elif tag == "a":
            self._hide_anchor_text = False
        elif tag in ("ol", "ul") and self._lists:
            self._lists.pop()
            self._pending_marker = None  # An empty last item has no text to mark
        elif tag in ("td", "th"):
            self._end_cell()
        elif tag == "tr":
            self._end_row()
        elif tag == "table" and self._tables:
            self._end_row()
            self._tables.pop()
        elif _HEADING_TAG.match(tag) and self._heading:
            self._write("\n\n")
            self._heading = False

        # After the tag's own handling, so e.g. a table's last row comes before the break.
        if tag in _BLOCK_TAGS:
            self._write_block_break()

    def handle_data(self, data: str) -> None:
        if self._div_depth == 0 or self._skip_depth > 0 or self._hide_anchor_text:
            return
        # The marker goes right before the item's first text, so it stays
        # on the same line even when the item starts with a <p>.
        if self._pending_marker is not None and data.strip():
            self._write(self._pending_marker + " ")
            self._pending_marker = None
        # Line breaks in the HTML source are not line breaks in the text.
        self._write(re.sub(r"\s+", " ", data))

    # --- Output -----------------------------------------------------------------

    def _write(self, text: str) -> None:
        self._buffers[-1].append(text)

    def _in_cell(self) -> bool:
        return any(row is not None and row.cell_open for row in self._tables)

    def _single_line(self) -> bool:
        """
        True while writing text that must stay on one line.
        """
        return self._heading or self._in_cell()

    def _line_break(self, normal: str) -> str:
        """
        The text for a break: `normal` in the body, a space in a heading
        and a cell break in a table cell.
        """
        if self._heading:
            return " "
        if self._in_cell():
            return _CELL_BREAK_MARK
        return normal

    def _write_block_break(self) -> None:
        self._write(self._line_break("\n\n"))

    # --- Footnotes --------------------------------------------------------------

    def _start_anchor(self, href: str | None) -> None:
        href = href or ""
        if (match := _FOOTNOTE_REF_HREF.match(href)) and self._footnote is None:
            self._write(f"[^{match[1]}]")
            self._hide_anchor_text = True      # Replaces the "[5]" of the page
        elif _FOOTNOTE_BACK_HREF.match(href):
            self._hide_anchor_text = True      # The "[5]" that starts a footnote

    def _start_footnote(self, div_id: str | None) -> None:
        match = _FOOTNOTE_ID.match(div_id or "")
        if match and self._footnote is None:
            self._footnote = (int(match[1]), self._div_depth)
            self._buffers.append([])

    def _end_footnote(self) -> None:
        if self._footnote is not None and self._footnote[1] == self._div_depth:
            number = self._footnote[0]
            self.footnotes[number] = normalize_blocks("".join(self._buffers.pop()))
            self._footnote = None

    # --- Tables -----------------------------------------------------------------

    def _start_row(self) -> None:
        if self._tables:
            self._end_row()  # In case the previous row is not closed
            self._tables[-1] = _OpenRow()

    def _end_row(self) -> None:
        row = self._tables[-1] if self._tables else None
        if row is None:
            return
        self._end_cell()
        self._tables[-1] = None
        cells = [cell for cell in row.cells if cell]
        if cells:
            self._write(" | ".join(cells) + "\n")

    def _start_cell(self) -> None:
        row = self._tables[-1] if self._tables else None
        if row is None:
            return
        self._end_cell()  # In case the previous cell is not closed
        self._buffers.append([])
        row.cell_open = True

    def _end_cell(self) -> None:
        row = self._tables[-1] if self._tables else None
        if row is None or not row.cell_open:
            return
        row.cells.append(_normalize_cell("".join(self._buffers.pop())))
        row.cell_open = False


def parse_list_start(value: str | None) -> int:
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


def format_list_number(number: int, style: str) -> str:
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
