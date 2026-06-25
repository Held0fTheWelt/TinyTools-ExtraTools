"""Resolve monorepo root and Contractify hub directory paths."""
from __future__ import annotations

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
    """Return the World of Shadows repository root (directory containing
    hub ``pyproject.toml``).

    Args:
        start: Primary start used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return resolve_project_root(
        start=start or Path.cwd(),
        env_var="CONTRACTIFY_REPO_ROOT",
        marker_text=None,
    )


def contractify_hub_dir(repo: Path | None = None) -> Path:
    """Return the Contractify hub directory (``'fy'-suites/contractify``).

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return _current_or_legacy_suite_dir(r, "contractify")
