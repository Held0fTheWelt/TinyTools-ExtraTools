"""Hub cli for testify.tools.

"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from testify.tools.repo_paths import repo_root
from testify.tools.test_governance import write_audit_bundle


def _print_help() -> None:
    """Print help.
    """
    print(
        'Testify hub CLI\n\n'
        'Commands:\n'
        '  audit      Audit test runner / CI / pyproject governance.\n'
        '  self-check Alias for audit using default report paths.\n'
    )


def _audit(args: argparse.Namespace) -> int:
    """Audit the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # _audit.
    root = repo_root()
    json_rel = args.out or "'fy'-suites/testify/reports/testify_audit.json"
    md_rel = args.md_out or "'fy'-suites/testify/reports/testify_audit_report.md"
    payload = write_audit_bundle(root, json_rel=json_rel, md_rel=md_rel)
    # Branch on not args.quiet so _audit only continues along the matching state path.
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
    parser = argparse.ArgumentParser(description='Testify repository test governance CLI')
    sub = parser.add_subparsers(dest='command', required=True)
    p_audit = sub.add_parser('audit', help='Write JSON + markdown audit outputs')
    p_audit.add_argument('--out', default='', help='Repo-relative JSON output path')
    p_audit.add_argument('--md-out', default='', help='Repo-relative markdown output path')
    p_audit.add_argument('--quiet', action='store_true')
    sub.add_parser('self-check', help='Run audit with default report paths')
    ns = parser.parse_args(argv)
    if ns.command == 'audit':
        return _audit(ns)
    if ns.command == 'self-check':
        return _audit(argparse.Namespace(out='', md_out='', quiet=False))
    return 2
