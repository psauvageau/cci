"""
List the decisions published on the Tax Court of Canada "browse by date" pages.

A year page (e.g. .../decisions/en/2024/nav_date.do) shows its decisions
25 at a time. The list itself is served by the iframe version of the page
(``?iframe=true``) and the following pages are reached with ``?page=N``.
"""
from __future__ import annotations

import logging
import re
import time
import random
from html.parser import HTMLParser
from typing import Generator, NamedTuple
from urllib.parse import urljoin

from ._http import get_html

_logger = logging.getLogger(__name__)

_DELAY_BETWEEN_PAGES_S = 10.0

# Path of a decision page, e.g. /tcc-cci/decisions/en/item/521380/index.do
_DECISION_PATH = re.compile(r"/decisions/[a-z]{2}/item/\d+/index\.do$")

# Text of the pager link that leads to the next page.
_NEXT_PAGE_TEXT = ">"


class DecisionListPage(NamedTuple):
    """
    What one page of the decision list contains.
    """
    decision_urls: list[str]
    has_next_page: bool


def fetch_decisions_url(url: str) -> Generator[str, None, None]:
    """
    Open the link for a specific year and yield the URL of each decision,
    following the pages of the list until the last one.
    """
    page = 1
    while True:
        _logger.debug("Fetching page %d of %s", page, url)
        html = fetch_list_page(url, page)
        result = parse_list_page(html, url)
        _logger.info("Found %d decision URLs on page %d", len(result.decision_urls), page)
        yield from result.decision_urls

        if not result.has_next_page:
            return
        page += 1
        time.sleep(_DELAY_BETWEEN_PAGES_S)


def fetch_list_page(url: str, page: int) -> str:
    """
    Download the HTML of one page of the decision list.
    """
    return get_html(url, params={"page": str(page), "iframe": "true"})


def parse_list_page(html: str, base_url: str) -> DecisionListPage:
    """
    Extract the absolute decision URLs, in page order and without duplicates,
    and whether the page links to a next page.
    """
    anchors = _AnchorCollector.collect(html)

    decision_urls: list[str] = []
    for href, _text in anchors:
        absolute = urljoin(base_url, href)
        if _DECISION_PATH.search(absolute) and absolute not in decision_urls:
            decision_urls.append(absolute)

    has_next_page = any(text == _NEXT_PAGE_TEXT for _href, text in anchors)
    return DecisionListPage(decision_urls, has_next_page)


class _AnchorCollector(HTMLParser):
    """
    Collect the (href, text) of every <a href=...> in an HTML document.
    """

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    @classmethod
    def collect(cls, html: str) -> list[tuple[str, str]]:
        parser = cls()
        parser.feed(html)
        parser.close()
        return parser.anchors

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text).strip()))
            self._href = None


def _wait()->None:
    time.sleep(random.uniform(1, _DELAY_BETWEEN_PAGES_S))
