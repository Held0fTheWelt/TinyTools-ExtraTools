"""End-to-end audit assembly (hermetic repo)."""
from __future__ import annotations

import contractify.tools.repo_paths as repo_paths
from contractify.tools.audit_pipeline import run_audit


def test_run_audit_includes_conflicts_relations_drifts() -> None:
    """Verify that run audit includes conflicts relations drifts works as
    expected.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_run_audit_includes_conflicts_relations_drifts.
    root = repo_paths.repo_root()
    payload = run_audit(root, max_contracts=40)
    assert payload["stats"]["n_contracts"] >= 8
    assert payload["stats"]["n_relations"] >= 4
    assert payload["stats"]["n_drifts"] >= 0
    assert payload["stats"]["n_conflicts"] >= 3
    assert any(r["relation"] == "supersedes" for r in payload["relations"])
    assert any(r["relation"] == "conflicts_with" for r in payload["relations"])
    assert any(c.get("classification") == "superseded_still_referenced_as_current" for c in payload["conflicts"])
    assert any("conflict:" in u for u in payload["actionable_units"])
