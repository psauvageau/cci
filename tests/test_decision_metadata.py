import unittest
from datetime import date
from pathlib import Path

from cci.decision_metadata import (
    DecisionMetadata,
    canonical_url,
    parse_decision_url,
    parse_metadata,
)

FIXTURES = Path(__file__).parent / "fixtures"
SITE = "https://decision.tcc-cci.ca"


def _parse_fixture(name: str, url: str) -> DecisionMetadata:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return parse_metadata(html, url)


class TestParseMetadataRecentEnglish(unittest.TestCase):
    """
    2026 decision in English, not yet translated.
    """

    meta: DecisionMetadata

    @classmethod
    def setUpClass(cls) -> None:
        cls.meta = _parse_fixture(
            "decision_521584_en.html",
            f"{SITE}/tcc-cci/decisions/en/item/521584/index.do?iframe=true",
        )

    def test_identity(self) -> None:
        self.assertEqual(self.meta.source_url, f"{SITE}/tcc-cci/decisions/en/item/521584/index.do")
        self.assertEqual(self.meta.item_id, 521584)
        self.assertEqual(self.meta.language, "en")
        self.assertEqual(self.meta.doc_id, "tcc-cci-521584-en")
        self.assertEqual(self.meta.court, "Tax Court of Canada")

    def test_metadata_table(self) -> None:
        self.assertEqual(self.meta.case_name, "Patel v. The King")
        self.assertEqual(self.meta.collection, "Tax Court of Canada Judgments")
        self.assertEqual(self.meta.decision_date, date(2026, 2, 17))
        self.assertEqual(self.meta.neutral_citation, "2026 TCC 33")
        self.assertEqual(self.meta.docket_numbers, ["2016-4571(IT)G", "2016-4750(IT)G"])
        self.assertEqual(self.meta.judges, ["Joanna Hill"])
        self.assertEqual(self.meta.subjects, ["Income Tax Act"])
        self.assertEqual(self.meta.other_fields, {})

    def test_links(self) -> None:
        self.assertEqual(self.meta.pdf_url, f"{SITE}/tcc-cci/decisions/en/521584/1/document.do")
        self.assertEqual(self.meta.other_languages, {})


class TestParseMetadataFrench(unittest.TestCase):
    """
    Decision in French, with an English version.
    """

    meta: DecisionMetadata

    @classmethod
    def setUpClass(cls) -> None:
        cls.meta = _parse_fixture(
            "decision_521417_fr.html",
            f"{SITE}/tcc-cci/decisions/fr/item/521417/index.do?iframe=true",
        )

    def test_french_labels_map_to_the_same_fields(self) -> None:
        self.assertEqual(self.meta.language, "fr")
        self.assertEqual(self.meta.case_name, "684761 B.C. Ltd. c. Le Roi")
        self.assertEqual(self.meta.collection, "Jugements de la Cour canadienne de l'impôt")
        self.assertEqual(self.meta.decision_date, date(2025, 3, 20))
        self.assertEqual(self.meta.neutral_citation, "2025 CCI 45")
        self.assertEqual(self.meta.docket_numbers, ["2013-3379(IT)G", "2017-381(IT)G"])
        self.assertEqual(self.meta.judges, ["David E. Spiro"])
        self.assertEqual(self.meta.subjects, ["Loi de l'impôt sur le revenu"])
        self.assertEqual(self.meta.other_fields, {})

    def test_links_to_the_english_version(self) -> None:
        self.assertEqual(
            self.meta.other_languages,
            {"en": f"{SITE}/tcc-cci/decisions/en/item/521417/index.do"},
        )


class TestParseMetadataOld(unittest.TestCase):
    """
    1996 decision: no neutral citation and no PDF.
    """

    meta: DecisionMetadata

    @classmethod
    def setUpClass(cls) -> None:
        cls.meta = _parse_fixture(
            "decision_25281_en.html",
            f"{SITE}/tcc-cci/decisions/en/item/25281/index.do",
        )

    def test_missing_fields_are_empty(self) -> None:
        self.assertEqual(self.meta.case_name, "Marshall v. The Queen")
        self.assertEqual(self.meta.decision_date, date(1996, 10, 16))
        self.assertIsNone(self.meta.neutral_citation)
        self.assertIsNone(self.meta.pdf_url)
        self.assertEqual(self.meta.docket_numbers, ["95-4067(IT)I"])
        self.assertEqual(self.meta.judges, ["Ronald D. Bell"])


def _page(rows: str) -> str:
    return (
        '<link rel="canonical" href="/tcc-cci/decisions/en/item/1/index.do" />'
        '<div class="metadata"><h3 class="title">A v. B</h3><table>'
        f"{rows}</table></div>"
    )


class TestParseMetadataEdgeCases(unittest.TestCase):

    URL = f"{SITE}/tcc-cci/decisions/en/item/1/index.do"

    def test_values_separated_by_br(self) -> None:
        meta = parse_metadata(_page(
            '<tr><td class="label">Subjects</td><td class="metadata">'
            "Income Tax Act<br/>Excise Tax Act<br/></tr>"
        ), self.URL)
        self.assertEqual(meta.subjects, ["Income Tax Act", "Excise Tax Act"])

    def test_unknown_label_is_kept(self) -> None:
        with self.assertLogs("cci.decision_metadata", level="WARNING"):
            meta = parse_metadata(_page(
                '<tr><td class="label">Appeal from</td><td class="metadata">Somewhere</tr>'
            ), self.URL)
        self.assertEqual(meta.other_fields, {"Appeal from": ["Somewhere"]})

    def test_invalid_date_is_none(self) -> None:
        with self.assertLogs("cci.decision_metadata", level="WARNING"):
            meta = parse_metadata(_page(
                '<tr><td class="label">Date</td><td class="metadata">October 16, 1996</tr>'
            ), self.URL)
        self.assertIsNone(meta.decision_date)

    def test_page_without_metadata_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_metadata("<html><body><p>Not found</p></body></html>", self.URL)


class TestUrlHelpers(unittest.TestCase):

    def test_parse_decision_url(self) -> None:
        self.assertEqual(
            parse_decision_url(f"{SITE}/tcc-cci/decisions/fr/item/521417/index.do"),
            (521417, "fr"),
        )

    def test_parse_decision_url_rejects_other_pages(self) -> None:
        with self.assertRaises(ValueError):
            parse_decision_url(f"{SITE}/tcc-cci/decisions/en/2024/nav_date.do")

    def test_canonical_url_removes_query_and_fragment(self) -> None:
        self.assertEqual(
            canonical_url(f"{SITE}/tcc-cci/decisions/en/item/1/index.do?iframe=true#x"),
            f"{SITE}/tcc-cci/decisions/en/item/1/index.do",
        )
