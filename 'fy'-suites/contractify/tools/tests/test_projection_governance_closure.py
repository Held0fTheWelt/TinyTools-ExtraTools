"""Tests for projection governance closure.

"""
from __future__ import annotations

import contractify.tools.repo_paths as repo_paths
from contractify.tools.audit_pipeline import run_audit
from contractify.tools.discovery import discover_contracts_and_projections


def test_projection_drifts_are_closed_on_real_repo() -> None:
    """Verify that projection drifts are closed on real repo works as
    expected.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_projection_drifts_are_closed_on_real_repo.
    payload = run_audit(repo_paths.repo_root(), max_contracts=60)
    drift_ids = {row["id"] for row in payload["drift_findings"]}
    assert "DRF-POSTMAN-OPENAPI-SHA-001" not in drift_ids
    assert not any(drift_id.startswith("DRF-PROJ-BACKREF-") for drift_id in drift_ids)


def test_api_and_websocket_projection_inventory_is_visible() -> None:
    """Verify that api and websocket projection inventory is visible works
    as expected.
    """
    contracts, projections, _relations = discover_contracts_and_projections(repo_paths.repo_root(), max_contracts=60)
    ids = {c.id for c in contracts}
    assert {
        "CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS",
        "CTR-RUNTIME-NARRATIVE-COMMIT",
        "CTR-AI-STORY-ROUTING-OBSERVATION",
        "CTR-EVIDENCE-BASELINE-GOVERNANCE",
    }.issubset(ids)
    proj_map = {p.path: p.source_contract_id for p in projections}
    assert proj_map["docs/api/README.md"] == "CTR-API-OPENAPI-001"
    assert proj_map["docs/api/REFERENCE.md"] == "CTR-API-OPENAPI-001"
    assert proj_map["docs/api/POSTMAN_COLLECTION.md"] == "CTR-API-OPENAPI-001"
    assert proj_map["postman/WEBSOCKET_MANUAL.md"] == "CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS"
