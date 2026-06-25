"""Hub cli for documentify.tools.

"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from documentify.tools.document_builder import write_generation_bundle
from documentify.tools.repo_paths import repo_root


def _print_help() -> None:
    """Print help.
    """
    print(
        'Documentify hub CLI\n\n'
        'Commands:\n'
        '  generate   Generate simple / technical / role-bound documentation.\n'
        '  audit      Alias for generate using default output locations.\n'
        '  self-check Alias for generate using default output locations.\n'
    )


def _generate(args: argparse.Namespace) -> int:
    """Generate the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Build filesystem locations and shared state that the rest of _generate reuses.
    root = repo_root()
    out_dir = args.out_dir or "'fy'-suites/documentify/generated"
    json_rel = args.out or "'fy'-suites/documentify/reports/documentify_audit.json"
    md_rel = args.md_out or "'fy'-suites/documentify/reports/documentify_generation_report.md"
    payload = write_generation_bundle(root, out_dir_rel=out_dir, json_rel=json_rel, md_rel=md_rel)
    # Branch on not args.quiet so _generate only continues along the matching state
    # path.
    if not args.quiet:
        print(json.dumps(payload, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

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
    if not argv or argv[0] in ('-h', '--help', 'help'):
        _print_help()
        return 0
    parser = argparse.ArgumentParser(description='Documentify documentation generation CLI')
    sub = parser.add_subparsers(dest='command', required=True)
    p_gen = sub.add_parser('generate', help='Generate documentation outputs')
    p_gen.add_argument('--out-dir', default='', help='Repo-relative output root for generated docs')
    p_gen.add_argument('--out', default='', help='Repo-relative JSON output path')
    p_gen.add_argument('--md-out', default='', help='Repo-relative markdown output path')
    p_gen.add_argument('--quiet', action='store_true')
    p_audit = sub.add_parser('audit', help='Alias for generate using default locations')
    p_audit.add_argument('--out-dir', default='', help='Repo-relative output root for generated docs')
    p_audit.add_argument('--out', default='', help='Repo-relative JSON output path')
    p_audit.add_argument('--md-out', default='', help='Repo-relative markdown output path')
    p_audit.add_argument('--quiet', action='store_true')
    p_check = sub.add_parser('self-check', help='Alias for generate using default locations')
    p_check.add_argument('--out-dir', default='', help='Repo-relative output root for generated docs')
    p_check.add_argument('--out', default='', help='Repo-relative JSON output path')
    p_check.add_argument('--md-out', default='', help='Repo-relative markdown output path')
    p_check.add_argument('--quiet', action='store_true')
    ns = parser.parse_args(argv)
    if ns.command in ('generate', 'audit', 'self-check'):
        return _generate(ns)
    return 2
