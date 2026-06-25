"""Tests for project resolver.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root


def test_resolver_uses_marker_text(tmp_path: Path) -> None:
    """Verify that resolver uses marker text works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    root = tmp_path / "repo"
    root.mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "pyproject.toml").write_text("name = 'example-hub'\n", encoding="utf-8")
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    resolved = resolve_project_root(start=nested, marker_text="example-hub")
    assert resolved == root


def test_resolver_accepts_manifest_without_marker_text(tmp_path: Path) -> None:
    """Verify that resolver accepts manifest without marker text works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    root = tmp_path / "repo"
    root.mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "fy-manifest.yaml").write_text("manifestVersion: 1\n", encoding="utf-8")
    nested = root / "x" / "y"
    nested.mkdir(parents=True)
    resolved = resolve_project_root(start=nested)
    assert resolved == root
