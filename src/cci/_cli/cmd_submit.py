"""
CLI command to submit a decision document to Pinecone.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cli_cmd import CliCmd

from .. import submit

_logger = logging.getLogger(__name__)


class CommandSubmit(CliCmd):
    """
    Submit a file to Pinecone.
    """
    title: str = "submit"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        """
        parser.add_argument(
            "file_name",
            type=Path,
            help="File to submit to Pinecone, e.g. a decision document such as 521584.en.md",
        )

    def run(self, args: argparse.Namespace) -> None:
        """
        Placeholder: not implemented yet.
        """
        _logger.info("Running %s command with %s", self.title, args.file_name)
        submit.submit_file(args.file_name)
