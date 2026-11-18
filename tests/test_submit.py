import unittest
from unittest import mock

import pinecone

from pathlib import Path

from cci.submit import ASSISTANT_NAME, batch_upload_files, check_file_exists, list_files


def _client(describe_file: mock.Mock) -> mock.Mock:
    """
    A stand-in for pinecone.Pinecone whose assistants.describe_file is `describe_file`.
    """
    pc = mock.Mock(spec=pinecone.Pinecone)
    pc.assistants.describe_file = describe_file
    return pc


class TestCheckFileExists(unittest.TestCase):

    def test_true_when_the_assistant_has_the_file(self) -> None:
        describe_file = mock.Mock(return_value=mock.Mock(status="Available"))

        self.assertTrue(check_file_exists(_client(describe_file), "521584-en"))
        describe_file.assert_called_once_with(assistant_name=ASSISTANT_NAME, file_id="521584-en")

    def test_false_when_the_file_is_not_found(self) -> None:
        describe_file = mock.Mock(side_effect=pinecone.NotFoundError())

        self.assertFalse(check_file_exists(_client(describe_file), "521584-en"))

    def test_uses_the_given_assistant(self) -> None:
        describe_file = mock.Mock(return_value=mock.Mock(status="Processing"))

        self.assertTrue(check_file_exists(_client(describe_file), "521584-fr", "other"))
        describe_file.assert_called_once_with(assistant_name="other", file_id="521584-fr")

    def test_other_errors_are_not_hidden(self) -> None:
        describe_file = mock.Mock(side_effect=pinecone.UnauthorizedError())

        with self.assertRaises(pinecone.UnauthorizedError):
            check_file_exists(_client(describe_file), "521584-en")


class TestListFiles(unittest.TestCase):

    def test_returns_every_file_of_the_assistant(self) -> None:
        files = [mock.Mock(id="521584-en"), mock.Mock(id="521584-fr")]
        pc = mock.Mock(spec=pinecone.Pinecone)
        pc.assistants.list_files.return_value.to_list.return_value = files

        self.assertEqual(list_files(pc), files)
        pc.assistants.list_files.assert_called_once_with(assistant_name=ASSISTANT_NAME)

    def test_uses_the_given_assistant(self) -> None:
        pc = mock.Mock(spec=pinecone.Pinecone)
        pc.assistants.list_files.return_value.to_list.return_value = []

        self.assertEqual(list_files(pc, "other"), [])
        pc.assistants.list_files.assert_called_once_with(assistant_name="other")


class TestBatchUploadFiles(unittest.TestCase):

    def setUp(self) -> None:
        self.pc = mock.Mock(spec=pinecone.Pinecone)
        self.pc.assistants.list_files.return_value.to_list.return_value = [
            mock.Mock(id="521584-en"),
        ]

    def uploaded_ids(self) -> list[str]:
        return [call.kwargs["file_id"] for call in self.pc.assistants.upload_file.call_args_list]

    def test_uploads_only_the_files_not_in_the_assistant(self) -> None:
        batch_upload_files(self.pc, "cci", [Path("521584.en.md"), Path("521584.fr.md")])

        self.assertEqual(self.uploaded_ids(), ["521584-fr"])
        self.pc.assistants.upload_file.assert_called_once_with(
            assistant_name="cci", file_path="521584.fr.md", file_id="521584-fr",
        )

    def test_lists_the_assistant_once_and_never_checks_files_one_by_one(self) -> None:
        batch_upload_files(self.pc, "cci", [Path("1.en.md"), Path("2.en.md"), Path("3.en.md")])

        self.pc.assistants.list_files.assert_called_once_with(assistant_name="cci")
        self.pc.assistants.describe_file.assert_not_called()
        self.assertEqual(self.uploaded_ids(), ["1-en", "2-en", "3-en"])

    def test_a_file_given_twice_is_uploaded_once(self) -> None:
        batch_upload_files(self.pc, "cci", [Path("1.en.md"), Path("sub/1.en.md")])

        self.assertEqual(self.uploaded_ids(), ["1-en"])
