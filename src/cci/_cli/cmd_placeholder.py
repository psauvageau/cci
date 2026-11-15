"""
This module defines a placeholder command for the Juris CLI.

It serves as an example of how to implement a new
command and can be used as a template for future commands.
"""

from __future__ import annotations

import argparse
import logging


from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)

class CommandPlaceholder(CliCmd):
    """
    A placeholder command for the Juris CLI.
    This command does not perform any meaningful action.
    """
    title: str = "placeholder"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--example', type=str, help='Example argument for the placeholder command')

    def run(self, args: argparse.Namespace) -> None:
        _logger.info(f"Running {self.title} command with example argument: {args.example}")
        print(f"Placeholder command executed with example argument: {args.example}")


