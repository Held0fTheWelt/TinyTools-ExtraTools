"""
Entry for ``python -m despaghettify.tools``.

With the hub under ``'fy'-suites/despaghettify/``, use ``pip install -e
.`` from the repo root (see ``pyproject.toml``) or set ``PYTHONPATH`` to
the ``'fy'-suites`` directory so ``import despaghettify`` resolves
before this module loads.
"""
from __future__ import annotations

from despaghettify.tools.hub_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
