"""
CLI command to get Tax Court of Canada decisions.
"""
from __future__ import annotations

import os
import argparse
import logging
import time
import random

from ..decision import default_file_name, get_decision
from ..decision_list import fetch_decisions_url
from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


# Link to the TCC decisions web site by date.
URL_PER_YEAR = "https://decision.tcc-cci.ca/tcc-cci/decisions/en/{year}/nav_date.do"

FIRST = 1995
LAST = 2026

_MAX_WAIT:float = 10.0

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
            year_url = URL_PER_YEAR.format(year=year)
            _logger.info("Fetching decisions for year %d from URL: %s", year, year_url)

            file_name = f"urls_list_{year}.txt"
            if not os.path.exists(file_name):
                urls = list(fetch_decisions_url(year_url))
                _logger.info("Writing %s", file_name)
                with open(file_name, "w") as f:
                    for decision_url in urls:                        
                        f.write(decision_url + "\n")
                _wait()
            else:
                _logger.info("File %s already exists, skipping fetch.", file_name)

        _logger.info("Processing URL list files to fetch decisions")
        for file_name in os.listdir("."):
            if file_name.startswith("urls_list_") and file_name.endswith(".txt"):
                with open(file_name, "r") as f:
                    for url in f:
                        url = url.strip()
                        if url:
                            _get_decision(url)




def _get_decision(url: str) -> None:
    _logger.info("Fetching decision from URL: %s", url)

    file_name = default_file_name(url)
    if os.path.exists(file_name):
        _logger.info("Decision already exists locally: %s", file_name)
        return

    decision = get_decision(url)
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(decision)
    _wait()


def _wait()->None:
    t = random.uniform(1, _MAX_WAIT)
    _logger.info("Waiting %s s",t)
    time.sleep(t)  # Sleep for a random interval to avoid hammering the server