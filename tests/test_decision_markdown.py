import re
import unittest
from pathlib import Path

from cci.decision_markdown import html_to_markdown

FIXTURES = Path(__file__).parent / "fixtures"

FOOTNOTE_REF = re.compile(r"\[\^(\d+)\](?!:)")
FOOTNOTE_DEF = re.compile(r"^\[\^(\d+)\]:", re.MULTILINE)


def _convert(body: str) -> str:
    return html_to_markdown(f'<div class="documentcontent">{body}</div>')


def _convert_fixture(name: str) -> str:
    return html_to_markdown((FIXTURES / name).read_text(encoding="utf-8"))


class TestParagraphs(unittest.TestCase):

    def test_paragraphs_are_separated_by_a_blank_line(self) -> None:
        self.assertEqual(
            _convert(
                '<p class="MsoNormal" align="right">Docket: 2016-4750(IT)G<o:p></o:p></p>'
                "<p><span>BETWEEN:</span></p>"
                "<p>Motion heard together with the motion of Paul Benninger,<br>\n"
                "     2016-4571(IT)G<o:p></o:p></p>"
                "<p><o:p>&nbsp;</o:p></p>"
                "<p>The appellant&#8217;s motion is <em>granted</em>.</p>"
            ),
            "Docket: 2016-4750(IT)G\n\n"
            "BETWEEN:\n\n"
            "Motion heard together with the motion of Paul Benninger,\n"
            "2016-4571(IT)G\n\n"
            "The appellant’s motion is granted.\n",
        )

    def test_ignores_text_outside_the_decision_and_scripts(self) -> None:
        markdown = html_to_markdown(
            '<h3 class="title">Patel v. The King</h3>'
            '<div class="documentcontent"><p>Inside</p><script>var x = 1;</script></div>'
            "<div>Outside</div>"
        )
        self.assertEqual(markdown, "Inside\n")

    def test_page_without_decision_raises(self) -> None:
        with self.assertRaises(ValueError):
            html_to_markdown("<html><body><p>Not found</p></body></html>")


class TestHeadings(unittest.TestCase):

    def test_heading_levels_start_at_two(self) -> None:
        self.assertEqual(
            _convert(
                "<h1><strong>A. Introduction</strong></h1>"
                "<h2>Step 5:</h2>"
                "<h4>(a) The motion is not timely</h4>"
            ),
            "## A. Introduction\n\n### Step 5:\n\n##### (a) The motion is not timely\n",
        )

    def test_heading_stays_on_one_line(self) -> None:
        self.assertEqual(_convert("<h1>A.<br>Intro<p>duction</p></h1>"), "## A. Intro duction\n")

    def test_empty_heading_is_dropped(self) -> None:
        self.assertEqual(_convert("<h1><o:p>&nbsp;</o:p></h1><p>Text</p>"), "Text\n")


class TestFootnotes(unittest.TestCase):

    # Same shape as the footnotes exported by Word on the TCC site.
    HTML = (
        '<p>[8] The debts.<a href="#_ftn5" name="_ftnref5" title="">'
        '<span class="MsoFootnoteReference">[5]</span></a> After.</p>'
        '<div style="mso-element:footnote-list"><hr>'
        '<div style="mso-element:footnote" id="ftn5">'
        '<p class="MsoFootnoteText"><a href="#_ftnref5" name="_ftn5" title="">'
        '<span class="MsoFootnoteReference">[5]</span></a><span> Separate appeals.</span></p>'
        "<p>Second paragraph.</p>"
        "</div></div>"
    )

    def test_reference_becomes_markdown_footnote(self) -> None:
        self.assertTrue(_convert(self.HTML).startswith("[8] The debts.[^5] After.\n"))

    def test_definitions_go_to_a_final_section(self) -> None:
        self.assertTrue(_convert(self.HTML).endswith(
            "## Footnotes\n\n[^5]: Separate appeals.\n\n    Second paragraph.\n"
        ))

    def test_no_footnotes_section_without_footnotes(self) -> None:
        self.assertNotIn("## Footnotes", _convert("<p>No notes.</p>"))


class TestTables(unittest.TestCase):

    def test_one_line_per_row_with_non_empty_cells(self) -> None:
        self.assertEqual(
            _convert(
                "<p>Appearances:</p>"
                "<table><tr><td><p>Counsel for the Appellant:</p></td><td></td>"
                "<td><p>Kristen Duerhammer</p><p>Shara Sullivan</p></td></tr>"
                "<tr><td>&nbsp;</td></tr>"
                "<tr><td>9(e)</td><td>The value is $29,317,478.</td></tr></table>"
                "<p>After</p>"
            ),
            "Appearances:\n\n"
            "Counsel for the Appellant: | Kristen Duerhammer; Shara Sullivan\n"
            "9(e) | The value is $29,317,478.\n\n"
            "After\n",
        )

    def test_unclosed_cells_and_rows(self) -> None:
        self.assertEqual(
            _convert("<table><tr><td>a<td>b<tr><td>c</table>"),
            "a | b\nc\n",
        )


class TestLists(unittest.TestCase):

    def test_numbers_items_on_the_same_line_as_their_text(self) -> None:
        # Same shape as the ORDER section of a real decision: <li><p>text</p></li>
        self.assertEqual(
            _convert(
                '<ol type="1" class="level1">'
                '<li><p class="MsoNormal"><!-- [if !supportLists] --><!-- [endif] -->'
                "<span>Leave is granted.</span></p></li>"
                "<li><p><span>Costs are awarded.</span></p></li>"
                "</ol>"
            ),
            "1. Leave is granted.\n\n2. Costs are awarded.\n",
        )

    def test_follows_type_and_start_attributes(self) -> None:
        self.assertEqual(
            _convert(
                '<ol type="a" start="3"><li>third</li><li>fourth</li></ol>'
                '<ol type="I"><li>one</li><li>two</li><li>three</li><li>four</li></ol>'
            ),
            "c. third\n\nd. fourth\n\nI. one\n\nII. two\n\nIII. three\n\nIV. four\n",
        )

    def test_nested_lists_are_indented(self) -> None:
        self.assertEqual(
            _convert(
                "<ol><li>first"
                '<ol type="i"><li>sub one</li><li>sub two</li></ol>'
                "</li><li>second</li></ol>"
            ),
            "1. first\n\n    i. sub one\n\n    ii. sub two\n\n2. second\n",
        )

    def test_unordered_list_items_get_a_dash(self) -> None:
        self.assertEqual(_convert("<ul><li>alpha</li><li>beta</li></ul>"), "- alpha\n\n- beta\n")

    def test_invalid_start_defaults_to_one(self) -> None:
        self.assertEqual(_convert('<ol start="x"><li>item</li></ol>'), "1. item\n")


class TestRealDecisions(unittest.TestCase):
    """
    Saved decision pages from the TCC site.
    """

    def assert_footnotes_match(self, markdown: str, expected_count: int) -> None:
        references = FOOTNOTE_REF.findall(markdown)
        definitions = FOOTNOTE_DEF.findall(markdown)
        self.assertEqual(len(definitions), expected_count)
        self.assertEqual(sorted(set(references), key=int), definitions)

    def assert_clean(self, markdown: str) -> None:
        self.assertNotIn("mso-", markdown)
        self.assertNotRegex(markdown, r"<[a-zA-Z/]")
        self.assertNotRegex(markdown, "[\x01\x02]")
        self.assertNotIn("\n\n\n", markdown)

    def test_recent_english_decision(self) -> None:
        markdown = _convert_fixture("decision_521584_en.html")
        self.assert_clean(markdown)
        self.assert_footnotes_match(markdown, 34)
        headings = re.findall(r"^#+ .*$", markdown, re.MULTILINE)
        self.assertEqual(headings[0], "## A. Introduction")
        self.assertIn("### Step 5:", headings)
        self.assertIn("##### (a) The motion is not timely", headings)
        self.assertEqual(headings[-1], "## Footnotes")
        self.assertIn("debts.[^5] After", markdown)
        self.assertIn(
            "\n[^5]: This issue is the subject of separate Tax Court appeals filed by the tax debtors.\n",
            markdown,
        )
        self.assertIn("\nCounsel for the Appellant: | Kristen Duerhammer; Shara Sullivan\n", markdown)
        self.assertIn("\n1. The Respondent’s request for leave", markdown)

    def test_french_decision(self) -> None:
        markdown = _convert_fixture("decision_521417_fr.html")
        self.assert_clean(markdown)
        self.assert_footnotes_match(markdown, 8)
        self.assertIn("\n## Analyse\n", markdown)

    def test_old_decision_without_headings_or_footnotes(self) -> None:
        markdown = _convert_fixture("decision_25281_en.html")
        self.assert_clean(markdown)
        self.assertTrue(markdown.startswith("Date: 19961016\n\nDocket: 95-4067(IT)I\n"))
        self.assertNotRegex(markdown, r"(?m)^#")
