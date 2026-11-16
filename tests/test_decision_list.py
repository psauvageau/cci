import unittest

from cci.decision_list import parse_list_page

BASE_URL = "https://decision.tcc-cci.ca/tcc-cci/decisions/en/2024/nav_date.do"

# Trimmed-down copy of the structure of a real list page.
PAGE_WITH_NEXT = """
<ul class="pager">
    <li class="active"><a target="_parent" href="/tcc-cci/decisions/en/2024/nav_date.do?page=2">2</a></li>
    <li class="active"><a target="_parent" href="/tcc-cci/decisions/en/2024/nav_date.do?page=2">&gt;</a></li>
</ul>
<div class="info"><h3>
    <span class="title"><a target="_parent" href="/tcc-cci/decisions/en/item/521380/index.do">Boles v. The King</a></span>
    - <span class="citation">2024 TCC 167</span>
</h3>
<a href="/tcc-cci/decisions/en/521380/1/document.do">PDF</a></div>
<div class="info"><h3>
    <span class="title"><a target="_parent" href="/tcc-cci/decisions/en/item/521375/index.do">Pilarski v. The King</a></span>
</h3></div>
<a href="/tcc-cci/decisions/en/item/521380/index.do">Boles again</a>
<a href="/tcc-cci/decisions/en/nav_alpha.do">Search by Case Name</a>
"""

LAST_PAGE = """
<ul class="pager">
    <li class="active"><a target="_parent" href="/tcc-cci/decisions/en/2024/nav_date.do?page=5">&lt;</a></li>
</ul>
<span class="title"><a href="/tcc-cci/decisions/en/item/521221/index.do">Last v. The King</a></span>
"""


class TestParseListPage(unittest.TestCase):

    def test_extracts_absolute_decision_urls_in_order_without_duplicates(self) -> None:
        result = parse_list_page(PAGE_WITH_NEXT, BASE_URL)
        self.assertEqual(
            result.decision_urls,
            [
                "https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521380/index.do",
                "https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521375/index.do",
            ],
        )

    def test_detects_next_page(self) -> None:
        self.assertTrue(parse_list_page(PAGE_WITH_NEXT, BASE_URL).has_next_page)

    def test_last_page_has_no_next_page(self) -> None:
        result = parse_list_page(LAST_PAGE, BASE_URL)
        self.assertFalse(result.has_next_page)
        self.assertEqual(len(result.decision_urls), 1)

    def test_page_without_decisions(self) -> None:
        result = parse_list_page("<html><body>Nothing here</body></html>", BASE_URL)
        self.assertEqual(result.decision_urls, [])
        self.assertFalse(result.has_next_page)
