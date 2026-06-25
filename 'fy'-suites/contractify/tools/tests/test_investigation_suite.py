"""Tests for investigation suite.

"""
from __future__ import annotations

from pathlib import Path

import contractify.tools.repo_paths as repo_paths
from contractify.tools.investigation_suite import write_adr_investigation_suite


def test_adr_investigation_suite_writes_markdown_and_mermaid() -> None:
    """Verify that adr investigation suite writes markdown and mermaid
    works as expected.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.
    """
    # Build filesystem locations and shared state that the rest of
    # test_adr_investigation_suite_writes_markdown_and_mermaid reuses.
    root = repo_paths.repo_root()
    out_dir_rel = "'fy'-suites/contractify/reports/_pytest_adr_investigation"
    out_dir = root / out_dir_rel
    # Protect the critical test_adr_investigation_suite_writes_markdown_and_mermaid work
    # so failures can be turned into a controlled result or cleanup path.
    try:
        bundle = write_adr_investigation_suite(root, out_dir_rel=out_dir_rel)
        assert bundle["adr_governance"]["stats"]["n_adrs"] >= 1
        md = out_dir / "ADR_GOVERNANCE_INVESTIGATION.md"
        rel_map = out_dir / "ADR_RELATION_MAP.mmd"
        conflict_map = out_dir / "ADR_CONFLICT_MAP.mmd"
        assert md.is_file()
        assert rel_map.is_file()
        assert conflict_map.is_file()
        assert "## ADR inventory" in md.read_text(encoding="utf-8")
        assert "graph TD" in rel_map.read_text(encoding="utf-8")
        assert "graph TD" in conflict_map.read_text(encoding="utf-8")
    finally:
        # Branch on out_dir.exists() so
        # test_adr_investigation_suite_writes_markdown_and_mermaid only continues along
        # the matching state path.
        if out_dir.exists():
            # Process child one item at a time so
            # test_adr_investigation_suite_writes_markdown_and_mermaid applies the same
            # rule across the full collection.
            for child in sorted(out_dir.glob("*"), reverse=True):
                child.unlink()
            out_dir.rmdir()
