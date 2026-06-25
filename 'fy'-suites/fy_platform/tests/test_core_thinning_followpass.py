"""Tests for core thinning followpass.

"""
from __future__ import annotations

from pathlib import Path


def _workspace_root() -> Path:
    """Workspace root.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[2]


def _line_count(path: Path) -> int:
    """Line count.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    return sum(1 for _ in path.open(encoding='utf-8'))


def test_followpass_targeted_shared_core_files_stay_thin() -> None:
    """Verify that followpass targeted shared core files stay thin works as
    expected.

    The implementation iterates over intermediate items before it
    returns.
    """
    workspace = _workspace_root()
    thresholds = {
        'fy_platform/ai/final_product.py': 80,
        'fy_platform/surfaces/public_cli.py': 60,
        'fy_platform/tools/cli.py': 150,
        'fy_platform/ai/semantic_index/index_manager.py': 250,
        'fy_platform/ai/evidence_registry/registry.py': 260,
    }
    # Process (rel, limit) one item at a time so
    # test_followpass_targeted_shared_core_files_stay_thin applies the same rule across
    # the full collection.
    for rel, limit in thresholds.items():
        assert _line_count(workspace / rel) < limit, rel
