"""
CLI command to count the words of the Markdown files in the current directory.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..cost_evaluation import count_words_in_files
from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


class CommandCostEvaluation(CliCmd):
    """
    Count the words of each Markdown file in the current directory.
    """
    title: str = "cost-evaluation"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        No arguments.
        """
        pass

    def run(self, args: argparse.Namespace) -> None:
        counts = list(count_words_in_files(Path.cwd()))
        _logger.info("Found %d Markdown files", len(counts))

        words = sum(counts)
        iu    = words / 300
        cost = 0.0005 * iu
                    

        print(f"Words  {words}")
        print(f"IU     {iu}")
        print(f"Cost   {cost}")
