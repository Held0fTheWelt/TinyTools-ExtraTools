"""Relation extension — bounded edges on top of discovery."""
from __future__ import annotations

import contractify.tools.repo_paths as repo_paths
from contractify.tools.conflicts import detect_all_conflicts
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.relations import extend_relations


def test_extend_relations_adds_normative_to_openapi_reference() -> None:
    """Verify that extend relations adds normative to openapi reference
    works as expected.
    """
    root = repo_paths.repo_root()
    contracts, projections, base = discover_contracts_and_projections(root, max_contracts=40)
    extended = extend_relations(root, contracts, projections, base)
    kinds = {(r.relation, r.source_id, r.target_id) for r in extended}
    assert ("references", "CTR-NORM-INDEX-001", "CTR-API-OPENAPI-001") in kinds


def test_extend_relations_supersedes_and_conflict_shadow_with_conflicts() -> None:
    """Verify that extend relations supersedes and conflict shadow with
    conflicts works as expected.
    """
    root = repo_paths.repo_root()
    contracts, projections, base = discover_contracts_and_projections(root, max_contracts=40)
    cids = frozenset(c.id for c in contracts)
    conflicts = detect_all_conflicts(root, projections, contract_ids=cids, contracts=contracts)
    extended = extend_relations(root, contracts, projections, base, conflicts=conflicts)
    kinds = {(r.relation, r.source_id, r.target_id) for r in extended}
    assert any(k[0] == "supersedes" for k in kinds)
    assert any(k[0] == "conflicts_with" for k in kinds)
