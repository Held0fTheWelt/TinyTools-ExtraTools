"""Tests for adr governance.

"""
from __future__ import annotations

from pathlib import Path

from contractify.tools.adr_governance import discover_adr_governance
from contractify.tools.minimal_repo import build_minimal_contractify_test_repo
import contractify.tools.repo_paths as repo_paths


def test_adr_governance_reports_canonical_inventory_and_targets() -> None:
    """Verify that adr governance reports canonical inventory and targets
    works as expected.

    The implementation iterates over intermediate items before it
    returns.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_adr_governance_reports_canonical_inventory_and_targets.
    root = repo_paths.repo_root()
    payload = discover_adr_governance(root)
    assert payload["canonical_dir"] == "docs/ADR"
    assert payload["stats"]["n_adrs"] >= 3
    assert payload["stats"]["n_legacy_adrs"] == 0
    assert not any(f["kind"] == "legacy_adr_location" for f in payload["findings"])
    # Process row one item at a time so
    # test_adr_governance_reports_canonical_inventory_and_targets applies the same rule
    # across the full collection.
    for row in payload["records"]:
        assert row["proposed_canonical_path"].startswith("docs/ADR/")
        assert row["proposed_canonical_id"].startswith("ADR.")


def test_adr_governance_detects_canonical_path_collision(tmp_path: Path) -> None:
    """Verify that adr governance detects canonical path collision works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    root = build_minimal_contractify_test_repo(tmp_path)
    adr = root / "docs" / "ADR"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (adr / "adr-0001-scene-identity-copy.md").write_text(
        "# ADR-0001: Scene identity\n\n**Status**: Accepted\n\nSame title, same family.\n",
        encoding="utf-8",
    )
    payload = discover_adr_governance(root)
    assert any(f["kind"] in {"duplicate_declared_id", "canonical_path_collision", "similar_title_overlap"} for f in payload["findings"])
