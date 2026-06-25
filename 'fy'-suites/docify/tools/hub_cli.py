"""
Docify hub CLI — audit, drift hints, inline explain, and backlog
helpers.

After ``pip install -e .`` from the repository root, use the ``docify``
console script, or:

python -m docify.tools audit --json --exit-zero python -m docify.tools
drift --json python -m docify.tools inline-explain --file
path/to/file.py --function some_fn

Script path (repo-relative):

python "./'fy'-suites/docify/tools/hub_cli.py" drift

See ``'fy'-suites/docify/README.md`` and ``documentation-check-task.md``
for governance flows.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from docify.tools.repo_paths import docify_hub_dir, repo_root

INPUT_LIST_NAME = "documentation_implementation_input.md"
OPEN_DOC_ROW = re.compile(r"^\|\s*\*\*(DOC-\d+)\*\*\s*\|")


def parse_open_doc_ids(markdown: str) -> list[str]:
    """Return sorted open **DOC-*** ids from backlog table rows.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        markdown: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    seen: set[str] = set()
    # Process line one item at a time so parse_open_doc_ids applies the same rule across
    # the full collection.
    for line in markdown.splitlines():
        match = OPEN_DOC_ROW.match(line)
        # Branch on match so parse_open_doc_ids only continues along the matching state
        # path.
        if match:
            seen.add(match.group(1))
    return sorted(seen, key=lambda value: int(value.split("-")[1]))


def _print_global_help() -> None:
    """Print global help.
    """
    print(
        "Docify hub CLI\n\n"
        "Commands:\n"
        "  audit …          Python AST docstring audit (pass-through; same flags as legacy script).\n"
        "  drift …          Heuristic documentation follow-up hints from git-changed paths.\n"
        "  inline-explain   Generate grouped inline explanations for one Python function.\n"
        "  bulk-document    Document a Python tree with docstrings and inline comments.\n"
        "  open-doc         Print open DOC-* backlog IDs from documentation_implementation_input.md.\n\n"
        "Examples:\n"
        "  docify audit --json --exit-zero --out 'fy'-suites/docify/reports/doc_audit.json\n"
        "  docify drift --json --out 'fy'-suites/docify/reports/doc_drift.json\n"
        "  docify inline-explain --file fy_platform/ai/base_adapter.py --function prepare_context_pack --mode dense\n"
        "  docify bulk-document --repo-root . --root . --apply\n"
    )


def cmd_open_doc(args: argparse.Namespace) -> int:
    """Print open DOC-* IDs from the canonical backlog table.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    if args.input is not None:
        path = Path(args.input).expanduser().resolve()
        if not path.is_file():
            print(f"Missing backlog file: {path}", file=sys.stderr)
            return 3
    else:
        root = repo_root()
        hub = docify_hub_dir(root)
        path = hub / INPUT_LIST_NAME
        if not path.is_file():
            print(f"Missing {path.relative_to(root)}", file=sys.stderr)
            return 3
    text = path.read_text(encoding="utf-8", errors="replace")
    for item in parse_open_doc_ids(text):
        print(item)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch ``docify`` subcommands.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_global_help()
        return 0
    if argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        print(f"Unknown flag: {argv[0]}", file=sys.stderr)
        _print_global_help()
        return 2

    cmd = argv[0]
    tail = argv[1:]

    if cmd == "audit":
        from docify.tools.python_documentation_audit import main as audit_main

        return int(audit_main(tail))

    if cmd == "drift":
        from docify.tools.documentation_drift import drift_cli_main

        return int(drift_cli_main(tail))

    if cmd == "inline-explain":
        from docify.tools.python_inline_explain import main as inline_main

        return int(inline_main(tail))

    if cmd == "bulk-document":
        from docify.tools.bulk_python_document import main as bulk_main

        return int(bulk_main(tail))

    if cmd == "open-doc":
        parser = argparse.ArgumentParser(description="List open DOC-* backlog rows.")
        parser.add_argument(
            "--input",
            type=Path,
            default=None,
            help=(
                "Path to documentation_implementation_input.md "
                "(default: resolve hub file via repo_root())."
            ),
        )
        ns = parser.parse_args(tail)
        return cmd_open_doc(ns)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    _print_global_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
