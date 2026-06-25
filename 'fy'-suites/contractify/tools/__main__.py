"""Enable ``python -m contractify.tools``."""
from __future__ import annotations

import sys

from contractify.tools.hub_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
