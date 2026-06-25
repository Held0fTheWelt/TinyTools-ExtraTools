"""Enable ``python -m docify.tools``."""
from __future__ import annotations

import sys

from docify.tools.hub_cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
