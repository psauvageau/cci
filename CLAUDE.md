# cci

A Python tool to download and process all the published decisions of the
Tax Court of Canada (Cour canadienne de l'impôt — "CCI").

## Stack

- Language: **Python 3.12**
- Project name and package/module name: **`cci`**
- Source code: `src/cci/` (src layout, packaged with setuptools via `pyproject.toml`)
- Tests: `tests/`
- Type checking: **mypy**
- Test runner: **pytest**

## Python environment

Always use the virtual environment at the project root: `.venv/`.
Never use the system Python or a global `pip`.

Windows paths (the project is developed on Windows):

```bash
.venv/Scripts/python.exe -m pip install -e .[dev]
```

Run every tool through the venv interpreter (`.venv/Scripts/python.exe -m <tool>`) so
the right packages are picked up.

## Static typing

All code must be statically typed and pass mypy:

- Annotate every function and method: all parameters and the return type (including `-> None`).
- Annotate module-level constants and class attributes where the type isn't obvious.
- Avoid `Any` unless there is no reasonable alternative; don't silence errors with
  `# type: ignore` without a specific error code and a reason.
- The package ships a `py.typed` marker.

Check:

```bash
.venv/Scripts/python.exe -m mypy src tests
```

## Tests

- Tests live in `tests/` and follow the **unittest** convention: files named `test_*.py`,
  classes subclassing `unittest.TestCase`, methods named `test_*`, using `self.assert*`.
- Tests are **run with pytest** (configured in `pytest.ini`, with coverage).
- Tests are typed and checked by mypy like the rest of the code.
- Unit tests must not hit the network; use saved fixtures or mocks for HTTP responses.

Run:

```bash
.venv/Scripts/python.exe -m pytest
```

## Code layout

- `src/cci/__main__.py` — CLI entry point (`cci` console script / `python -m cci`).
  Holds the `COMMANDS` list of registered subcommands and sets up logging.
- `src/cci/_cli/cli_cmd.py` — `CliCmd` abstract base class for subcommands.
- `src/cci/_cli/cmd_<name>.py` — one file per subcommand. A command only parses and
  validates its arguments, then delegates to logic in a separate module outside `_cli`.
- `src/cci/_misc.py` — helpers (logging setup, debug data logging).
- `src/cci/_http.py` — `get_html()`: the one place that sends HTTP requests (user agent, timeout).
- `src/cci/decision_list.py` — list the decision URLs of a year ("browse by date" pages).
- `src/cci/decision.py` — `get_decision(url)`: download one decision and build its document.
- `src/cci/decision_metadata.py` — parse the metadata of a decision page (`DecisionMetadata`).
- `src/cci/decision_markdown.py` — convert the decision HTML to Markdown (body only).
- `src/cci/decision_document.py` — the output format: YAML front matter + title + body.
- `tests/fixtures/` — saved decision pages (2026 English, French, 1996) used by the tests.

The pages of the TCC site only contain their content in the iframe version
(`?iframe=true`). The output documents are meant for an LLM agent through RAG:
keep them machine-friendly (stable keys, JSON-compatible metadata) rather than pretty.

To add a subcommand, use the `create-cli-command` skill (`.claude/skills/create-cli-command/`).

## Conventions

- Use `logging` (module-level `_logger = logging.getLogger(__name__)`), not `print`, for
  diagnostics. `print` is for the command's actual output.
- Raise exceptions from command code instead of calling `exit()`; `main()` logs them and
  exits with code 1.
- Downloaded data is untrusted input: parse it defensively.

## Before finishing a change

1. `.venv/Scripts/python.exe -m mypy src tests` passes.
2. `.venv/Scripts/python.exe -m pytest` passes.
