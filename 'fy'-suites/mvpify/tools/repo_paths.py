"""Repo paths for mvpify.tools.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.workspace import workspace_root


def resolve_repo_root(raw: str | None = None) -> Path:
    """Resolve repo root.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        raw: Primary raw used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    # Branch on raw so resolve_repo_root only continues along the matching state path.
    if raw:
        return workspace_root(Path(raw).resolve())
    return workspace_root(Path(__file__).resolve())


def suite_root(repo_root: Path) -> Path:
    """Suite root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return repo_root / 'mvpify'


def reports_root(repo_root: Path) -> Path:
    """Reports root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return suite_root(repo_root) / 'reports'


def state_root(repo_root: Path) -> Path:
    """State root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return suite_root(repo_root) / 'state'


def imports_root(repo_root: Path) -> Path:
    """Imports root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return suite_root(repo_root) / 'imports'


def docs_imports_root(repo_root: Path) -> Path:
    """Docs imports root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return repo_root / 'docs' / 'MVPs' / 'imports'
