import dataclasses
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cci.decision_document import (
    FORMAT_VERSION,
    document_title,
    read_document,
    render_document,
)
from cci.decision_markdown import html_to_markdown
from cci.decision_metadata import DecisionMetadata, parse_metadata

FIXTURES = Path(__file__).parent / "fixtures"
SITE = "https://decision.tcc-cci.ca"
RETRIEVED_AT = datetime(2026, 11, 15, 20, 46, 6, tzinfo=timezone.utc)

EXPECTED_KEYS = [
    "format_version", "doc_id", "source_url", "pdf_url", "item_id", "language",
    "other_languages", "court", "collection", "case_name", "neutral_citation",
    "decision_date", "docket_numbers", "judges", "subjects", "other_fields",
    "retrieved_at",
]


PATEL = DecisionMetadata(
    source_url=f"{SITE}/tcc-cci/decisions/en/item/521584/index.do",
    item_id=521584,
    language="en",
    case_name="Patel v. The King",
    collection="Tax Court of Canada Judgments",
    decision_date=date(2026, 2, 17),
    neutral_citation="2026 TCC 33",
    docket_numbers=["2016-4571(IT)G", "2016-4750(IT)G"],
    judges=["Joanna Hill"],
    subjects=["Income Tax Act"],
    pdf_url=f"{SITE}/tcc-cci/decisions/en/521584/1/document.do",
)


def _metadata(**changes: Any) -> DecisionMetadata:
    """
    The Patel metadata, with some fields changed.
    """
    return dataclasses.replace(PATEL, **changes)


class TestRenderDocument(unittest.TestCase):

    def test_layout(self) -> None:
        document = render_document(_metadata(), "Body text.\n", RETRIEVED_AT)
        self.assertTrue(document.startswith("---\nformat_version: 1\ndoc_id: tcc-cci-521584-en\n"))
        self.assertTrue(document.endswith("---\n\n# Patel v. The King, 2026 TCC 33\n\nBody text.\n"))

    def test_front_matter_round_trip(self) -> None:
        fields, rest = read_document(render_document(_metadata(), "Body text.\n", RETRIEVED_AT))
        self.assertEqual(list(fields), EXPECTED_KEYS)
        self.assertEqual(fields["format_version"], FORMAT_VERSION)
        self.assertEqual(fields["source_url"], f"{SITE}/tcc-cci/decisions/en/item/521584/index.do")
        self.assertEqual(fields["item_id"], 521584)
        self.assertEqual(fields["court"], "Tax Court of Canada")
        self.assertEqual(fields["decision_date"], "2026-02-17")
        self.assertEqual(fields["docket_numbers"], ["2016-4571(IT)G", "2016-4750(IT)G"])
        self.assertEqual(fields["retrieved_at"], "2026-11-15T20:46:06Z")
        self.assertEqual(rest, "# Patel v. The King, 2026 TCC 33\n\nBody text.\n")

    def test_front_matter_is_json_compatible(self) -> None:
        fields, _rest = read_document(render_document(_metadata(), "Body.", RETRIEVED_AT))
        self.assertEqual(json.loads(json.dumps(fields)), fields)

    def test_missing_values_are_null_or_empty_but_present(self) -> None:
        metadata = DecisionMetadata(
            source_url=f"{SITE}/tcc-cci/decisions/en/item/25281/index.do",
            item_id=25281,
            language="en",
        )
        fields, rest = read_document(render_document(metadata, "Body.", RETRIEVED_AT))
        self.assertEqual(list(fields), EXPECTED_KEYS)
        self.assertIsNone(fields["neutral_citation"])
        self.assertIsNone(fields["pdf_url"])
        self.assertIsNone(fields["decision_date"])
        self.assertEqual(fields["judges"], [])
        self.assertEqual(fields["other_languages"], {})
        self.assertTrue(rest.startswith("# tcc-cci-25281-en\n"))

    def test_special_characters_round_trip(self) -> None:
        name = "Société 'X': #1 c. Sa Majesté \"la\" Reine"
        fields, _rest = read_document(render_document(
            _metadata(case_name=name, subjects=["Loi de l'impôt sur le revenu"]), "Body.", RETRIEVED_AT
        ))
        self.assertEqual(fields["case_name"], name)
        self.assertEqual(fields["subjects"], ["Loi de l'impôt sur le revenu"])

    def test_accents_are_written_as_is(self) -> None:
        document = render_document(_metadata(subjects=["Loi de l'impôt"]), "Body.", RETRIEVED_AT)
        self.assertIn("impôt", document)

    def test_retrieved_at_is_converted_to_utc(self) -> None:
        eastern = timezone(timedelta(hours=-5))
        moment = datetime(2026, 11, 15, 15, 46, 6, 123456, tzinfo=eastern)
        fields, _rest = read_document(render_document(_metadata(), "Body.", moment))
        self.assertEqual(fields["retrieved_at"], "2026-11-15T20:46:06Z")


class TestDocumentTitle(unittest.TestCase):

    def test_title_without_citation(self) -> None:
        self.assertEqual(
            document_title(_metadata(case_name="Marshall v. The Queen", neutral_citation=None)),
            "Marshall v. The Queen",
        )


class TestReadDocument(unittest.TestCase):

    def test_rejects_document_without_front_matter(self) -> None:
        with self.assertRaises(ValueError):
            read_document("# Title\n\nBody\n")

    def test_rejects_front_matter_that_is_not_a_mapping(self) -> None:
        with self.assertRaises(ValueError):
            read_document("---\n- a\n- b\n---\n\n# Title\n")


class TestRealDecision(unittest.TestCase):

    def test_french_fixture(self) -> None:
        html = (FIXTURES / "decision_521417_fr.html").read_text(encoding="utf-8")
        url = f"{SITE}/tcc-cci/decisions/fr/item/521417/index.do?iframe=true"
        document = render_document(parse_metadata(html, url), html_to_markdown(html), RETRIEVED_AT)

        fields, rest = read_document(document)
        self.assertEqual(fields["doc_id"], "tcc-cci-521417-fr")
        self.assertEqual(fields["other_languages"], {"en": f"{SITE}/tcc-cci/decisions/en/item/521417/index.do"})
        self.assertEqual(fields["subjects"], ["Loi de l'impôt sur le revenu"])
        self.assertTrue(rest.startswith("# 684761 B.C. Ltd. c. Le Roi, 2025 CCI 45\n\n"))
        self.assertIn("\n## Footnotes\n", rest)
