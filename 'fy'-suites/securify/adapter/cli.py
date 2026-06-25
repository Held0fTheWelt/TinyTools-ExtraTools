"""Command-line interface for securify.adapter.

"""
from fy_platform.ai.adapter_cli_helper import run_adapter_cli
from securify.adapter.service import SecurifyAdapter


def main(argv=None) -> int:
    """Run the command-line entry point.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    return int(run_adapter_cli(SecurifyAdapter, argv))
