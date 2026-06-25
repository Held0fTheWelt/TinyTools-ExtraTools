"""Repo paths for observifyfy.tools.

"""
from __future__ import annotations

from pathlib import Path

LEGACY_NESTED_DIRNAME = "'fy'-suites"
INTERNAL_DIRNAME = 'internal'


def resolve_repo_root(start: str | Path | None = None) -> Path:
    """Resolve repo root.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        start: Primary start used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    path = Path(start or '.').resolve()
    # Process candidate one item at a time so resolve_repo_root applies the same rule
    # across the full collection.
    for candidate in [path, *path.parents]:
        # Branch on (candidate / 'pyproject.toml').exists() and (... so
        # resolve_repo_root only continues along the matching state path.
        if (candidate / 'pyproject.toml').exists() and ((candidate / '.fydata').exists() or (candidate / 'fy_platform').exists()):
            return candidate
    return path


def fy_internal_root(repo_root: Path) -> Path:
    """Fy internal root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return repo_root


def fy_docs_root(repo_root: Path) -> Path:
    """Fy docs root.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    direct = repo_root / 'docs'
    legacy = repo_root / LEGACY_NESTED_DIRNAME / 'docs'
    if legacy.exists() and not direct.exists():
        return legacy
    return direct


def fy_internal_root_mirror(repo_root: Path) -> Path:
    """Fy internal root mirror.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return repo_root / INTERNAL_DIRNAME


def fy_adr_root(repo_root: Path) -> Path:
    """Fy adr root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return fy_docs_root(repo_root) / 'ADR'


def fy_observifyfy_root(repo_root: Path) -> Path:
    """Fy observifyfy root.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    direct = repo_root / 'observifyfy'
    legacy = repo_root / LEGACY_NESTED_DIRNAME / 'observifyfy'
    internal = repo_root / INTERNAL_DIRNAME / 'observifyfy'
    if direct.exists():
        return direct
    if internal.exists():
        return internal
    if legacy.exists():
        return legacy
    return direct


def ensure_internal_layout(repo_root: Path) -> dict[str, str]:
    """Ensure internal layout.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    created = {}
    for path in [fy_docs_root(repo_root), fy_adr_root(repo_root), fy_observifyfy_root(repo_root), fy_observifyfy_root(repo_root) / 'reports', fy_observifyfy_root(repo_root) / 'state']:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created[str(path.relative_to(repo_root))] = 'created'
    return created
