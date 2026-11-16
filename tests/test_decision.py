import unittest
from unittest import mock

from cci.decision import extract_decision_text, get_decision

# Trimmed-down copy of the structure of a real decision page.
DECISION_PAGE = """
<html><body>
<div class="metadata"><h3 class="title">Patel v. The King</h3></div>
<div id="document-content">
<div class="documentcontent"><div lang="en">
 <div class="WordSection1">
  <p class="MsoNormal" align="right">Docket: 2016-4750(IT)G<o:p></o:p></p>
  <p class="MsoNormal"><span>BETWEEN:<o:p></o:p></span></p>
  <p class="MsoNormal" align="center"><span>Motion heard together with the motion of Paul Benninger,<br>
     2016-4571(IT)G, on August 22, 2025<o:p></o:p></span></p>
  <p class="MsoNormal"><o:p>&nbsp;</o:p></p>
  <h1><strong>A. Introduction</strong></h1>
  <p>The appellant&#8217;s motion is <em>granted</em>.</p>
  <script>var ignored = 1;</script>
 </div>
</div></div>
</div>
<div class="footer">Not part of the decision</div>
</body></html>
"""


class TestExtractDecisionText(unittest.TestCase):

    def test_extracts_paragraphs_separated_by_blank_lines(self) -> None:
        self.assertEqual(
            extract_decision_text(DECISION_PAGE),
            "Docket: 2016-4750(IT)G\n"
            "\n"
            "BETWEEN:\n"
            "\n"
            "Motion heard together with the motion of Paul Benninger,\n"
            "2016-4571(IT)G, on August 22, 2025\n"
            "\n"
            "A. Introduction\n"
            "\n"
            "The appellant’s motion is granted.\n",
        )

    def test_ignores_text_outside_the_decision(self) -> None:
        text = extract_decision_text(DECISION_PAGE)
        self.assertNotIn("Patel v. The King", text)
        self.assertNotIn("Not part of the decision", text)
        self.assertNotIn("ignored", text)

    def test_page_without_decision_raises(self) -> None:
        with self.assertRaises(ValueError):
            extract_decision_text("<html><body><p>Not found</p></body></html>")


def _decision(body: str) -> str:
    return f'<div class="documentcontent">{body}</div>'


class TestListNumbering(unittest.TestCase):

    def test_numbers_ordered_list_items_on_the_same_line_as_their_text(self) -> None:
        # Same shape as the ORDER section of a real decision: <li><p>text</p></li>
        html = _decision(
            '<ol type="1" class="level1">'
            '<li><p class="MsoNormal"><!-- [if !supportLists] --><!-- [endif] -->'
            '<span>Leave is granted.</span></p></li>'
            '<li><p><span>Costs are awarded.</span></p></li>'
            '</ol>'
        )
        self.assertEqual(extract_decision_text(html), "1. Leave is granted.\n\n2. Costs are awarded.\n")

    def test_follows_type_and_start_attributes(self) -> None:
        html = _decision(
            '<ol type="a" start="3"><li>third</li><li>fourth</li></ol>'
            '<ol type="I"><li>one</li><li>two</li><li>three</li><li>four</li></ol>'
        )
        self.assertEqual(
            extract_decision_text(html),
            "c. third\n\nd. fourth\n\nI. one\n\nII. two\n\nIII. three\n\nIV. four\n",
        )

    def test_nested_lists_are_numbered_independently(self) -> None:
        html = _decision(
            '<ol><li>first'
            '<ol type="i"><li>sub one</li><li>sub two</li></ol>'
            '</li><li>second</li></ol>'
        )
        self.assertEqual(
            extract_decision_text(html),
            "1. first\n\ni. sub one\n\nii. sub two\n\n2. second\n",
        )

    def test_unordered_list_items_get_a_dash(self) -> None:
        html = _decision("<ul><li>alpha</li><li>beta</li></ul>")
        self.assertEqual(extract_decision_text(html), "- alpha\n\n- beta\n")

    def test_invalid_start_defaults_to_one(self) -> None:
        html = _decision('<ol start="x"><li>item</li></ol>')
        self.assertEqual(extract_decision_text(html), "1. item\n")


class TestGetDecision(unittest.TestCase):

    def test_requests_the_iframe_version_of_the_page(self) -> None:
        url = "https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521584/index.do"
        with mock.patch("cci.decision.get_html", return_value=DECISION_PAGE) as get_html:
            text = get_decision(url)
        get_html.assert_called_once_with(url, params={"iframe": "true"})
        self.assertTrue(text.startswith("Docket: 2016-4750(IT)G"))
