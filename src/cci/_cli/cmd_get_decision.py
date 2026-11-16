"""
CLI command to save one Tax Court of Canada decision as a Markdown document.
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
    Get one decision and save it as a Markdown document with its metadata.
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
            help="Markdown file (.md) where the decision is saved, "
                 "with its metadata in YAML front matter",
        )

    def run(self, args: argparse.Namespace) -> None:
        output: Path = args.output
        _logger.info("Getting decision %s", args.url)
        document = get_decision(args.url)
        output.write_text(document, encoding="utf-8")
        _logger.info("Saved %d characters to %s", len(document), output)
