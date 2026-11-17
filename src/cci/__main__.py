"""
Juris CLI entry point.
"""
import argparse
import logging
import argparse
import logging
from typing import  Type, Iterable, Optional, Generator, Final
from contextlib import contextmanager

from ._cli.cli_cmd import CliCmd
from ._cli.cmd_rss import CommandRss
from ._cli.cmd_get import CommandGet
from ._cli.cmd_get_decision import CommandGetDecision
from ._cli.cmd_submit import CommandSubmit
from ._cli.cmd_cost_evaluation import CommandCostEvaluation


from ._misc import init_logging

_logger = logging.getLogger()

COMMANDS :list[Type[CliCmd]] = [
    CommandRss,
    CommandGet,
    CommandGetDecision,
    CommandSubmit,
    CommandCostEvaluation,
]

def main()->None:
    """
    Main entry point for the LegalCodex CLI tool.
    """
    args: argparse.Namespace = _get_args(COMMANDS)

    

    with init_logging(args.verbose):

        if args.command:# Execute the command
            try:
                _logger.info("Starting")
                args.command.run(args)
                _logger.info("Finished successfully")
            except Exception as e:
                logging.error("Error: %s", e, exc_info=True)
                exit(1)
        else:
            _cmds = ", ".join([cmd.title for cmd in COMMANDS])
            print(f"No command specified. [{_cmds}]")
            exit(1)

def _get_args(cmds:list[Type[CliCmd]]) -> argparse.Namespace:
    """
    Create the main argument parser for the CLI
    """
    parser:argparse.ArgumentParser = argparse.ArgumentParser(
        description="CCI Command Line Interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--verbose', '-v',action="store_true", help='Enable verbose output')


    subparsers :argparse.Action = parser.add_subparsers()
    parser.set_defaults(command=None)

    # Register the command classes
    for cmd in cmds:
        cmd().register(subparsers)

    return parser.parse_args()


if __name__ == "__main__":
    main()
