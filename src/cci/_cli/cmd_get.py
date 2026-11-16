"""
CLI command to get Tax Court of Canada decisions.
"""
from __future__ import annotations

import argparse
import logging

from ..decision_list import fetch_decisions_url
from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


# Link to the TCC decisions web site by date.
URL_PER_YEAR = "https://decision.tcc-cci.ca/tcc-cci/decisions/en/{year}/nav_date.do"


FIRST = 1995
LAST = 2026


class CommandGet(CliCmd):
    """
    Get Tax Court of Canada decisions using the web-side access per date.
    """
    title: str = "get"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        No arguments yet.
        """
        pass

    def run(self, args: argparse.Namespace) -> None:
        """
        Placeholder: not implemented yet.
        """
        _logger.info("Running %s command", self.title)

        for year in range(LAST, FIRST, - 1):            
            url = URL_PER_YEAR.format(year=year)
            _logger.info("Fetching decisions for year %d from URL: %s", year, url)
            for decision_url in fetch_decisions_url(url):
                _logger.info("Found decision URL: %s", decision_url)



