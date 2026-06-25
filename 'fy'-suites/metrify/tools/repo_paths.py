"""Repo paths for metrify.tools.

"""
from __future__ import annotations

import os
from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

INTERNAL_DIRNAME = 'internal'


def repo_root(*, start: Path | None = None) -> Path:
    """Repo root.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        start: Primary start used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    env = os.environ.get('METRIFY_REPO_ROOT', '').strip()
    # Branch on env so repo_root only continues along the matching state path.
    if env:
        forced = Path(env).expanduser().resolve()
        # Branch on forced.is_dir() so repo_root only continues along the matching state
        # path.
        if forced.is_dir():
            return forced
    return resolve_project_root(start=start or Path.cwd(), marker_text=None)


def suite_dir(repo: Path | None = None) -> Path:
    """Suite dir.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return r / 'metrify'


def fy_suite_dir(repo: Path | None = None) -> Path:
    """Fy suite dir.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return r / INTERNAL_DIRNAME / 'metrify'
