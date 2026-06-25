"""Command-line interface for contractify.adapter.

"""
from __future__ import annotations

from fy_platform.ai.adapter_cli_helper import run_adapter_cli
from contractify.adapter.service import ContractifyAdapter


def main(argv=None) -> int:
    """Run the command-line entry point.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    return run_adapter_cli(ContractifyAdapter, argv)


if __name__ == '__main__':
    raise SystemExit(main())
