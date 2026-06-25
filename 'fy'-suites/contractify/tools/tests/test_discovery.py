"""Tests for discovery.

"""
import contractify.tools.repo_paths as repo_paths
from contractify.tools.discovery import discover_contracts_and_projections, projection_backref_ok


def test_discovery_finds_normative_index() -> None:
    """Verify that discovery finds normative index works as expected.
    """
    root = repo_paths.repo_root()
    contracts, projections, relations = discover_contracts_and_projections(root, max_contracts=40)
    ids = {c.id for c in contracts}
    assert "CTR-NORM-INDEX-001" in ids
    assert any(c.anchor_location.endswith("normative-contracts-index.md") for c in contracts)


def test_projection_backref_detects_link() -> None:
    """Verify that projection backref detects link works as expected.
    """
    root = repo_paths.repo_root()
    sample = root / "docs" / "dev" / "README.md"
    assert sample.is_file()
    ok, _reason = projection_backref_ok(sample)
    assert ok


def test_postman_manifest_projection_when_openapi_present() -> None:
    """Verify that postman manifest projection when openapi present works
    as expected.
    """
    root = repo_paths.repo_root()
    assert (root / "docs" / "api" / "openapi.yaml").is_file()
    _c, projections, _r = discover_contracts_and_projections(root, max_contracts=40)
    assert any(p.id.startswith("PRJ-POSTMANIFY") for p in projections)


def test_discovery_includes_ops_and_schema_when_present() -> None:
    """Verify that discovery includes ops and schema when present works as
    expected.
    """
    root = repo_paths.repo_root()
    contracts, _p, _r = discover_contracts_and_projections(root, max_contracts=40)
    types = {c.contract_type for c in contracts}
    assert "operational_runbook" in types
    assert "json_schema" in types


def test_discovery_includes_fy_suite_handoff_tasks() -> None:
    """Verify that discovery includes fy suite handoff tasks works as
    expected.
    """
    root = repo_paths.repo_root()
    contracts, _p, _r = discover_contracts_and_projections(root, max_contracts=50)
    ids = {c.id for c in contracts}
    assert "CTR-POSTMANIFY-TASK-001" in ids
    assert "CTR-DOCIFY-TASK-001" in ids
