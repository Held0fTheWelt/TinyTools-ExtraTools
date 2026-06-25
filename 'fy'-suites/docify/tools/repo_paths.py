"""Resolve monorepo root and Docify hub directory paths."""
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
    """Return project root via shared resolver with manifest-friendly
    fallback.

    Args:
        start: Primary start used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    forced = os.environ.get("DOCIFY_REPO_ROOT", "").strip()
    if forced:
        forced_path = Path(forced).expanduser().resolve()
        if forced_path.is_dir():
            return forced_path
    return resolve_project_root(start=start or Path.cwd(), marker_text=None)




def docify_hub_dir(repo: Path | None = None) -> Path:
    """Docify hub dir.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return _current_or_legacy_suite_dir(r, 'docify')


def docify_hub_rel_posix(repo: Path | None = None) -> str:
    """Hub directory as a repo-relative POSIX path for messages.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    r = repo or repo_root()
    return docify_hub_dir(r).relative_to(r).as_posix()
