"""Backup manager for fy_platform.ai.

"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, workspace_root, write_json

BACKUP_ROOT_REL = Path('.fydata/backups')
MANAGED_PATHS = [
    Path('.fydata/registry/registry.db'),
    Path('.fydata/index/semantic_index.db'),
    Path('.fydata/registry/schema_versions.json'),
    Path('.fydata/bindings'),
    Path('fy-manifest.yaml'),
    Path('pyproject.toml'),
    Path('requirements.txt'),
    Path('requirements-dev.txt'),
    Path('requirements-test.txt'),
]


def _copy_item(src: Path, dst: Path) -> None:
    """Copy item.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        src: Primary src used by this step.
        dst: Primary dst used by this step.
    """
    # Branch on src.is_dir() so _copy_item only continues along the matching state path.
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def create_workspace_backup(root: Path | None = None, *, reason: str = 'manual') -> dict[str, Any]:
    """Create workspace backup.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.
        reason: Primary reason used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    backup_id = f"backup-{utc_now().replace(':', '').replace('-', '').replace('.', '')}"
    backup_dir = workspace / BACKUP_ROOT_REL / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in MANAGED_PATHS:
        src = workspace / rel
        if not src.exists():
            continue
        dst = backup_dir / rel
        _copy_item(src, dst)
        copied.append(rel.as_posix())
    manifest = {
        'schema_version': 'fy.backup-manifest.v1',
        'backup_id': backup_id,
        'created_at': utc_now(),
        'reason': reason,
        'workspace_root': str(workspace),
        'paths': copied,
    }
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(backup_dir / 'backup_manifest.json', manifest)
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(workspace / BACKUP_ROOT_REL / 'latest.json', manifest)
    return manifest


def list_backups(root: Path | None = None) -> list[dict[str, Any]]:
    """List backups.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    backups_root = workspace / BACKUP_ROOT_REL
    if not backups_root.is_dir():
        return []
    out = []
    for path in sorted(backups_root.glob('backup-*')):
        manifest = path / 'backup_manifest.json'
        if manifest.is_file():
            try:
                out.append(json.loads(manifest.read_text(encoding='utf-8')))
            except json.JSONDecodeError:
                continue
    return out


def rollback_workspace_backup(root: Path | None = None, *, backup_id: str | None = None) -> dict[str, Any]:
    """Rollback workspace backup.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        backup_id: Identifier used to select an existing run or record.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    backups_root = workspace / BACKUP_ROOT_REL
    manifest_payload = None
    if backup_id:
        manifest_path = backups_root / backup_id / 'backup_manifest.json'
        if manifest_path.is_file():
            manifest_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    else:
        latest = backups_root / 'latest.json'
        if latest.is_file():
            manifest_payload = json.loads(latest.read_text(encoding='utf-8'))
    if not manifest_payload:
        return {'ok': False, 'reason': 'backup_not_found'}
    backup_dir = backups_root / manifest_payload['backup_id']
    restored: list[str] = []
    for rel_text in manifest_payload.get('paths', []):
        rel = Path(rel_text)
        src = backup_dir / rel
        dst = workspace / rel
        if not src.exists():
            continue
        if dst.exists() and dst.is_dir() and not src.is_dir():
            shutil.rmtree(dst)
        if dst.exists() and dst.is_file() and src.is_dir():
            dst.unlink()
        if dst.exists() and dst.is_dir() and src.is_dir():
            shutil.rmtree(dst)
        _copy_item(src, dst)
        restored.append(rel.as_posix())
    return {
        'ok': True,
        'backup_id': manifest_payload['backup_id'],
        'restored_paths': restored,
    }
