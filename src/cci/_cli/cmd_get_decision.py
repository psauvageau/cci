"""
CLI command to save the text of one Tax Court of Canada decision to a file.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..decision import get_decision
from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


class CommandGetDecision(CliCmd):
    """
    Get the text of one decision and save it to a file.
    """
    title: str = "get-decision"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        """
        parser.add_argument(
            "url",
            type=str,
            help="URL of a decision, as returned by the get command "
                 "(e.g. https://decision.tcc-cci.ca/tcc-cci/decisions/en/item/521584/index.do)",
        )
        parser.add_argument(
            "output",
            type=Path,
            help="File where the text of the decision is saved",
        )

    def run(self, args: argparse.Namespace) -> None:
        output: Path = args.output
        _logger.info("Getting decision %s", args.url)
        text = get_decision(args.url)
        output.write_text(text, encoding="utf-8")
        _logger.info("Saved %d characters to %s", len(text), output)
