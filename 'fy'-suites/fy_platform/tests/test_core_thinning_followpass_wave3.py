"""Tests for core thinning followpass wave3.

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


def test_followpass_wave3_shared_core_files_stay_thinner() -> None:
    """Verify that followpass wave3 shared core files stay thinner works as
    expected.

    The implementation iterates over intermediate items before it
    returns.
    """
    workspace = _workspace_root()
    thresholds = {
        'fy_platform/ai/status_page.py': 60,
        'fy_platform/ai/release_readiness.py': 40,
        'fy_platform/ai/production_readiness.py': 40,
        'fy_platform/ai/final_product_catalog.py': 40,
        'fy_platform/tools/ai_suite_cli.py': 80,
    }
    # Process (rel, limit) one item at a time so
    # test_followpass_wave3_shared_core_files_stay_thinner applies the same rule across
    # the full collection.
    for rel, limit in thresholds.items():
        assert _line_count(workspace / rel) < limit, rel
