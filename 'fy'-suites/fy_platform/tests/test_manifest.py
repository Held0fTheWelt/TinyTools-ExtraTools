"""Tests for manifest.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.core.manifest import load_manifest, roots_for_suite


def test_load_manifest_reads_versioned_manifest(tmp_path: Path) -> None:
    """Verify that load manifest reads versioned manifest works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    p = tmp_path / "fy-manifest.yaml"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    p.write_text(
        "manifestVersion: 1\n"
        "suites:\n"
        "  docify:\n"
        "    roots:\n"
        "      - src\n",
        encoding="utf-8",
    )
    # Read and normalize the input data before
    # test_load_manifest_reads_versioned_manifest branches on or transforms it further.
    manifest, warnings = load_manifest(tmp_path)
    assert manifest is not None
    assert warnings == []
    assert roots_for_suite(manifest=manifest, suite_name="docify") == ["src"]


def test_load_manifest_reports_missing_version(tmp_path: Path) -> None:
    """Verify that load manifest reports missing version works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / "fy-manifest.yaml").write_text("suites: {}\n", encoding="utf-8")
    _manifest, warnings = load_manifest(tmp_path)
    assert "manifest_missing_manifestVersion" in warnings
