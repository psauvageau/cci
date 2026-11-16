import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from cci.decision import decision_document, get_decision
from cci.decision_document import read_document

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521584/index.do"
PAGE = (FIXTURES / "decision_521584_en.html").read_text(encoding="utf-8")


class TestDecisionDocument(unittest.TestCase):

    def test_document_has_metadata_title_and_body(self) -> None:
        retrieved_at = datetime(2026, 11, 15, 20, 46, 6, tzinfo=timezone.utc)
        fields, rest = read_document(decision_document(PAGE, URL, retrieved_at))

        self.assertEqual(fields["source_url"], URL)
        self.assertEqual(fields["neutral_citation"], "2026 TCC 33")
        self.assertEqual(fields["retrieved_at"], "2026-11-15T20:46:06Z")
        self.assertTrue(rest.startswith("# Patel v. The King, 2026 TCC 33\n\nDocket: 2016-4750(IT)G\n"))
        self.assertIn("\n## A. Introduction\n", rest)
        self.assertIn("\n[^5]: This issue is the subject", rest)


class TestGetDecision(unittest.TestCase):

    def test_downloads_the_iframe_version_once(self) -> None:
        with mock.patch("cci.decision.get_html", return_value=PAGE) as get_html:
            document = get_decision(URL)
        get_html.assert_called_once_with(URL, params={"iframe": "true"})

        fields, _rest = read_document(document)
        self.assertEqual(fields["doc_id"], "tcc-cci-521584-en")
        retrieved_at = datetime.fromisoformat(fields["retrieved_at"])
        self.assertLess(abs((datetime.now(timezone.utc) - retrieved_at).total_seconds()), 60)
