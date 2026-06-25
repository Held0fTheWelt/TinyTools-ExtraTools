"""Workspace for fy_platform.ai.

"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fy_platform.ai.workspace_docs import write_platform_doc_artifacts
from fy_platform.ai.workspace_hashing import sha256_bytes, sha256_text, slugify
from fy_platform.ai.workspace_io import read_text_safe, write_json, write_text
from fy_platform.ai.workspace_layout import (
    LEGACY_NESTED_DIRNAME,
    INTERNAL_DIRNAME,
    binding_path,
    ensure_workspace_layout,
    fy_suites_root,
    internal_adr_root,
    internal_docs_root,
    internal_platform_docs_root,
    internal_root,
    internal_run_dir,
    legacy_nested_root,
    migrate_legacy_nested_layout,
    suite_hub_dir,
    workspace_root,
)


def utc_now() -> str:
    """Utc now.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return datetime.now(timezone.utc).isoformat()


def target_repo_id(target_repo_root: Path) -> str:
    """Target repo id.

    Args:
        target_repo_root: Root directory used to resolve
            repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return slugify(target_repo_root.name) + '-' + sha256_text(str(target_repo_root.resolve()))[:8]

__all__ = [
    'LEGACY_NESTED_DIRNAME', 'INTERNAL_DIRNAME', 'binding_path', 'ensure_workspace_layout', 'fy_suites_root',
    'internal_adr_root', 'internal_docs_root', 'internal_platform_docs_root', 'internal_root', 'internal_run_dir',
    'legacy_nested_root', 'migrate_legacy_nested_layout', 'read_text_safe', 'sha256_bytes', 'sha256_text',
    'slugify', 'suite_hub_dir', 'target_repo_id', 'utc_now', 'workspace_root', 'write_json', 'write_platform_doc_artifacts',
    'write_text',
]
