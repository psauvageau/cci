import tempfile
import unittest
from pathlib import Path

from cci.cost_evaluation import FileWordCount, count_words, count_words_in_files


class TestCountWords(unittest.TestCase):

    def test_splits_on_any_whitespace(self) -> None:
        self.assertEqual(count_words("one two\tthree\nfour\r\n  five  "), 5)

    def test_punctuation_stays_with_its_word(self) -> None:
        # "#", "v." and "King," each count as one word.
        self.assertEqual(count_words("# Patel v. The King, 2026 TCC 33"), 8)

    def test_empty_text_has_no_words(self) -> None:
        self.assertEqual(count_words(" \n\t"), 0)


class TestCountWordsInFiles(unittest.TestCase):

    def test_counts_only_markdown_files_sorted_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "b.en.md").write_text("three words here", encoding="utf-8")
            (directory / "a.fr.md").write_text("décision de la Cour", encoding="utf-8")
            (directory / "notes.txt").write_text("not counted", encoding="utf-8")
            (directory / "sub.md").mkdir()

            counts = count_words_in_files(directory)

        self.assertEqual(
            counts,
            [FileWordCount(directory / "a.fr.md", 4), FileWordCount(directory / "b.en.md", 3)],
        )

    def test_empty_directory_gives_no_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(count_words_in_files(Path(tmp)), [])
