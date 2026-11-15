"""
CLI command to fetch the documents listed in a Tax Court of Canada RSS feed.
"""
from __future__ import annotations

import argparse
import logging

from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


DEFAULT = "https://decision.tcc-cci.ca/tcc-cci/decisions/fr/rss.do"


class CommandRss(CliCmd):
    """
    Get the documents referenced by a Tax Court of Canada RSS feed.
    """
    title: str = "rss"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        """
        parser.add_argument(
            "url",
            type=str,
            nargs="?",
            default=DEFAULT,
            help="URL of an RSS feed from the Tax Court of Canada decisions web site",
        )

    def run(self, args: argparse.Namespace) -> None:
        """
        Not implemented yet.
        """
        _logger.info("Fetching RSS feed from URL: %s", args.url)
