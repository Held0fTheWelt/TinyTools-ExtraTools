"""Hub cli for securify.tools.

"""
from __future__ import annotations

from typing import Sequence

from securify.tools.scanner import main as scanner_main


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    return int(scanner_main(argv))


if __name__ == '__main__':
    raise SystemExit(main())
