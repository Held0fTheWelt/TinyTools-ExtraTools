"""Resolve repository and suite paths for delagecy."""

from __future__ import annotations

import os
from pathlib import Path

FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(start: Path | None = None) -> Path:
    """Resolve the monorepo root."""
    env = os.environ.get("DELAGECY_REPO_ROOT", "").strip()
    if env:
        forced = Path(env).expanduser().resolve()
        if forced.is_dir():
            return forced
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / FY_SUITES_DIRNAME).is_dir() and (candidate / "pyproject.toml").is_file():
            return candidate
    return current


def suite_dir(root: Path | None = None) -> Path:
    """Return the delagecy suite directory."""
    base = root or repo_root()
    nested = base / FY_SUITES_DIRNAME / "delagecy"
    if nested.is_dir():
        return nested
    return Path(__file__).resolve().parents[1]


def registry_path(root: Path | None = None) -> Path:
    """Return the machine registry path."""
    return suite_dir(root) / "delagecy_registry.json"


def default_tracker_path(root: Path | None = None) -> Path:
    """Return the human tracker path."""
    return suite_dir(root) / "legacy_removal_tracker.md"
