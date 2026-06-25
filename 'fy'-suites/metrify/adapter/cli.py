"""Command-line interface for metrify.adapter.

"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .service import MetrifyAdapter


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
    # Read and normalize the input data before main branches on or transforms it
    # further.
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description='Metrify adapter CLI')
    sub = parser.add_subparsers(dest='command', required=True)

    p_audit = sub.add_parser('audit', help='Audit a target repo and write metrify artifacts')
    p_audit.add_argument('target_repo_root')

    # Read and normalize the input data before main branches on or transforms it
    # further.
    p_init = sub.add_parser('init', help='Bind metrify to a target repo')
    p_init.add_argument('target_repo_root')

    sub.add_parser('inspect', help='Inspect latest metrify state')
    # Read and normalize the input data before main branches on or transforms it
    # further.
    ns = parser.parse_args(argv)
    adapter = MetrifyAdapter()
    # Branch on ns.command == 'init' so main only continues along the matching state
    # path.
    if ns.command == 'init':
        out = adapter.init(ns.target_repo_root)
    # Branch on ns.command == 'inspect' so main only continues along the matching state
    # path.
    elif ns.command == 'inspect':
        out = adapter.inspect()
    else:
        out = adapter.audit(ns.target_repo_root)
    print(json.dumps(out, indent=2))
    return 0
