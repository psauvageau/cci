---
name: create-cli-command
description: Scaffold a new subcommand for the `cci` CLI. Use when adding a command to this project, e.g. "add a download command", "create a new CLI command", "make a `cci <name>` subcommand". Creates `src/cci/_cli/cmd_<name>.py` (a `CliCmd` subclass) and registers it in `src/cci/__main__.py`.
---

# Create a New CLI Command

Scaffold a new command in `src/cci/_cli/` and register it in the CLI entry point.

## Goal

- Create a new command file in `src/cci/_cli/`.
- Make the command class inherit from `CliCmd` (`src/cci/_cli/cli_cmd.py`).
- Implement the `run()` method.
- Register the command in `src/cci/__main__.py` so it is available from the CLI.

## Design rule

The command class is only responsible for **parsing and validating command-line arguments**.
It then delegates the actual work to a function in a separate module (for example
`src/cci/<name>.py`, or a subpackage for larger features). Do not put business logic
in the `_cli` module.

## Steps

1. Create `src/cci/_cli/cmd_<name>.py`.
2. Add a class named `Command<Name>(CliCmd)`.
3. Set `title` to the CLI command name (what the user types after `cci`).
4. Implement it following this template:

```python
"""
<One-line description of the command.>
"""
from __future__ import annotations

import argparse
import logging

from .cli_cmd import CliCmd

_logger = logging.getLogger(__name__)


class CommandName(CliCmd):
    title: str = "name"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command specific arguments to the parser.
        """
        pass

    def run(self, args: argparse.Namespace) -> None:
        # Validate args here, then delegate:
        # from ..name import do_name
        # do_name(...)
        pass
```

5. Update `src/cci/__main__.py`, matching the existing import style:
   - Add `from ._cli.cmd_<name> import Command<Name>`
   - Add `Command<Name>,` to the `COMMANDS` list

## Verification

Run from the project root using the project venv (`.venv`). If the package is not
installed in the venv, either run `.venv/Scripts/pip install -e .[dev]` or set
`PYTHONPATH=src` for the check.

- `python -m cci --help` lists the new command.
- `python -m cci <name> --help` resolves successfully and shows its arguments.

## Notes

- Keep the command minimal; add arguments later via `add_arguments()`.
- `--verbose/-v` is a global flag handled in `__main__.py`; don't redefine it per command.
- Errors raised from `run()` are logged and turn into exit code 1 by `main()`, so
  raise exceptions rather than calling `exit()` inside a command.
