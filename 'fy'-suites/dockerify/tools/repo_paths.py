"""Repo paths for dockerify.tools.

"""
from __future__ import annotations

import os
from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

FY_SUITES_DIRNAME = "'fy'-suites"



def _current_or_legacy_suite_dir(repo: Path, suite: str) -> Path:
    """Current or legacy suite dir.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo: Primary repo used by this step.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    direct = repo / suite
    # Branch on direct.is_dir() or (repo / 'fy_platform').is_... so
    # _current_or_legacy_suite_dir only continues along the matching state path.
    if direct.is_dir() or (repo / 'fy_platform').is_dir():
        return direct
    nested = repo / FY_SUITES_DIRNAME / suite
    return nested


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
    env = os.environ.get('DOCKERIFY_REPO_ROOT', '').strip()
    if env:
        forced = Path(env).expanduser().resolve()
        if forced.is_dir():
            return forced
    return resolve_project_root(start=start or Path.cwd(), marker_text=None)


def dockerify_hub_dir(repo: Path | None = None) -> Path:
    """Dockerify hub dir.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return _current_or_legacy_suite_dir(r, 'dockerify')
