"""Workspace layout for fy_platform.ai.

"""
from __future__ import annotations

import shutil
from pathlib import Path

LEGACY_NESTED_DIRNAME = "'fy'-suites"
INTERNAL_DIRNAME = 'internal'


def workspace_root(start: Path | None = None) -> Path:
    """Workspace root.

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
    # Build filesystem locations and shared state that the rest of workspace_root
    # reuses.
    start = (start or Path(__file__)).resolve()
    explicit_dir = start if start.is_dir() else None
    # Process ancestor one item at a time so workspace_root applies the same rule across
    # the full collection.
    for ancestor in [start, *start.parents]:
        # Branch on ancestor.is_dir() and (ancestor / 'fy_governa... so workspace_root
        # only continues along the matching state path.
        if ancestor.is_dir() and (ancestor / 'fy_governance_enforcement.yaml').is_file():
            return ancestor
        # Branch on ancestor.is_dir() and (ancestor / 'README.md'... so workspace_root
        # only continues along the matching state path.
        if ancestor.is_dir() and (ancestor / 'README.md').is_file() and (ancestor / 'fy_platform').is_dir():
            return ancestor
    # Branch on explicit_dir is not None so workspace_root only continues along the
    # matching state path.
    if explicit_dir is not None:
        return explicit_dir
    raise RuntimeError(f'Could not resolve fy workspace root from {start}')


def legacy_nested_root(workspace: Path) -> Path:
    """Legacy nested root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / LEGACY_NESTED_DIRNAME


def internal_root(workspace: Path) -> Path:
    """Internal root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / INTERNAL_DIRNAME


def fy_suites_root(workspace: Path) -> Path:
    """Fy suites root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace


def internal_docs_root(workspace: Path) -> Path:
    """Internal docs root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return fy_suites_root(workspace) / 'docs'


def internal_adr_root(workspace: Path) -> Path:
    """Internal adr root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return internal_docs_root(workspace) / 'ADR'


def internal_platform_docs_root(workspace: Path) -> Path:
    """Internal platform docs root.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return internal_docs_root(workspace) / 'platform'


def migrate_legacy_nested_layout(workspace: Path) -> dict[str, list[str]]:
    """Migrate legacy nested layout.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        dict[str, list[str]]:
            Structured payload describing the outcome of the
            operation.
    """
    migrated: list[str] = []
    legacy = legacy_nested_root(workspace)
    if not legacy.is_dir():
        return {'migrated': migrated}
    for rel in ['docs', 'docs/ADR', 'docs/platform']:
        src = legacy / rel
        dst = workspace / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.rglob('*'):
                if item.is_dir():
                    continue
                target = dst / item.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(item, target)
                    migrated.append(str(target.relative_to(workspace)))
    return {'migrated': migrated}


def ensure_workspace_layout(root: Path) -> dict[str, list[str] | str]:
    """Ensure workspace layout.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, list[str] | str]:
            Structured payload describing the outcome of the
            operation.
    """
    created: list[str] = []
    for rel in [
        '.fydata/registry/objects', '.fydata/index', '.fydata/journal', '.fydata/runs', '.fydata/cache',
        '.fydata/bindings', '.fydata/backups', '.fydata/metrics', 'docs', 'docs/ADR', 'docs/platform',
        'internal', 'internal/docs', 'internal/docs/ADR', 'internal/docs/platform',
    ]:
        p = root / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(rel)
    migration = migrate_legacy_nested_layout(root)
    return {'workspace_root': str(root), 'created': created, 'migrated': migration['migrated']}


def suite_hub_dir(workspace: Path, suite: str) -> Path:
    """Suite hub dir.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / suite


def internal_run_dir(workspace: Path, suite: str, run_id: str) -> Path:
    """Internal run dir.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.
        run_id: Identifier used to select an existing run or record.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / '.fydata' / 'runs' / suite / run_id


def binding_path(workspace: Path, suite: str) -> Path:
    """Binding path.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / '.fydata' / 'bindings' / f'{suite}.json'
