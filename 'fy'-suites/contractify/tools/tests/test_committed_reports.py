"""
Committed ``reports/committed/*.json`` stay aligned with live
audit/discover payloads.
"""
from __future__ import annotations

import json
from pathlib import Path

_AUDIT_KEYS = frozenset(
    {
        "generated_at",
        "repo_root",
        "contracts",
        "projections",
        "relations",
        "drift_findings",
        "conflicts",
        "actionable_units",
        "stats",
        "disclaimer",
    }
)
_DISCOVER_KEYS = frozenset(
    {
        "generated_at",
        "repo_root",
        "contracts",
        "projections",
        "relations",
        "automation_tiers_sample",
    }
)


def _committed_dir() -> Path:
    """Committed dir.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[2] / "reports" / "committed"


def test_committed_audit_fixture_is_substantive() -> None:
    """Verify that committed audit fixture is substantive works as
    expected.
    """
    # Read and normalize the input data before
    # test_committed_audit_fixture_is_substantive branches on or transforms it further.
    path = _committed_dir() / "audit.hermetic-fixture.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert _AUDIT_KEYS <= data.keys()
    assert data["generated_at"] == "2026-04-13T18:00:00+00:00"
    assert data["repo_root"] == "<synthetic-minimal-repo-contractify-fixtures>"
    assert data["stats"]["n_contracts"] >= 8
    assert data["stats"]["n_relations"] >= 4
    assert data["stats"]["n_conflicts"] >= 3
    assert any(c.get("classification") == "superseded_still_referenced_as_current" for c in data["conflicts"])
    assert any(r.get("relation") == "supersedes" for r in data["relations"])


def test_committed_discover_fixture_matches_discover_shape() -> None:
    """Verify that committed discover fixture matches discover shape works
    as expected.
    """
    path = _committed_dir() / "discover.hermetic-fixture.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert _DISCOVER_KEYS <= data.keys()
    assert data["generated_at"] == "2026-04-13T18:00:00+00:00"
    assert data["repo_root"] == "<synthetic-minimal-repo-contractify-fixtures>"
    assert len(data["contracts"]) >= 8
