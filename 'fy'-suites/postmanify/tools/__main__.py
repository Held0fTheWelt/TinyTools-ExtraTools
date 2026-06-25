"""
Entry for ``python -m postmanify.tools`` (requires ``pip install -e .``
from repo root).
"""
from __future__ import annotations

from postmanify.tools.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
