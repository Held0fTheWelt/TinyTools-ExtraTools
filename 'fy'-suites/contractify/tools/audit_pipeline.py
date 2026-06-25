"""Assemble discovery, drift, conflicts, and actionable inventory messages."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contractify.tools.adr_governance import discover_adr_governance
from contractify.tools.conflicts import detect_all_conflicts
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.drift_analysis import run_all_drifts
from contractify.tools.models import automation_tier, serialise
from contractify.tools.relations import extend_relations
from contractify.tools.runtime_mvp_spine import PRECEDENCE_RULES, build_runtime_mvp_spine


def build_discover_payload(
    repo: Path,
    *,
    max_contracts: int = 30,
    frozen_generated_at: str | None = None,
) -> dict[str, Any]:
    """Same JSON shape as ``hub_cli discover`` (conflict-aware relations).

    Args:
        repo: Primary repo used by this step.
        max_contracts: Primary max contracts used by this step.
        frozen_generated_at: Primary frozen generated at used by this
            step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    contracts, projections, relations = discover_contracts_and_projections(
        repo,
        max_contracts=max_contracts,
    )
    cids = frozenset(c.id for c in contracts)
    conflicts = detect_all_conflicts(
        repo,
        projections,
        contract_ids=cids,
        contracts=contracts,
    )
    relations = extend_relations(repo, contracts, projections, relations, conflicts=conflicts)
    _spine_contracts, _spine_projections, _spine_relations, spine_conflicts, families = build_runtime_mvp_spine(repo)
    adr_governance = discover_adr_governance(repo)
    return {
        "generated_at": frozen_generated_at or datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo),
        "contracts": [serialise(c) for c in contracts],
        "projections": [serialise(p) for p in projections],
        "relations": [serialise(r) for r in relations],
        "automation_tiers_sample": {
            "0.95": automation_tier(0.95),
            "0.75": automation_tier(0.75),
            "0.4": automation_tier(0.4),
        },
        "execution_profile": {"mode": "discover", "max_contracts": max_contracts},
        "precedence_rules": PRECEDENCE_RULES,
        "adr_governance": adr_governance,
        "runtime_mvp_families": families,
        "manual_unresolved_areas": [serialise(c) for c in spine_conflicts],
    }


def build_actionable_units(drifts: list[Any], conflicts: list[Any]) -> list[str]:
    """Human-oriented backlog strings (not raw counts).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        drifts: Primary drifts used by this step.
        conflicts: Primary conflicts used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    units: list[str] = []
    for d in drifts:
        units.append(f"[{d.severity}] {d.summary} → {d.recommended_follow_up}")
    for c in conflicts:
        if c.requires_human_review or c.confidence >= 0.9:
            tag = "conflict" if c.requires_human_review else "conflict-deterministic"
            who = ", ".join(c.sources[:5])
            sev = getattr(c, "severity", "medium")
            units.append(f"[conflict:{sev}|{tag}] {c.summary} (sources: {who})")
    return units


def run_audit(
    repo: Path,
    *,
    max_contracts: int = 30,
    frozen_generated_at: str | None = None,
) -> dict[str, Any]:
    """Full machine-readable audit (restart-safe JSON contract).

    The implementation iterates over intermediate items before it
    returns.

    Args:
        repo: Primary repo used by this step.
        max_contracts: Primary max contracts used by this step.
        frozen_generated_at: Primary frozen generated at used by this
            step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    contracts, projections, relations = discover_contracts_and_projections(
        repo,
        max_contracts=max_contracts,
    )
    drifts = run_all_drifts(repo, contracts)
    cids = frozenset(c.id for c in contracts)
    conflicts = detect_all_conflicts(
        repo,
        projections,
        contract_ids=cids,
        contracts=contracts,
    )
    relations = extend_relations(repo, contracts, projections, relations, conflicts=conflicts)
    _spine_contracts, _spine_projections, _spine_relations, spine_conflicts, families = build_runtime_mvp_spine(repo)
    adr_governance = discover_adr_governance(repo)

    # attach drift ids onto contracts (lightweight cross-index)
    drift_by_contract: dict[str, list[str]] = {}
    for d in drifts:
        for cid in d.involved_contract_ids:
            drift_by_contract.setdefault(cid, []).append(d.id)
    for c in contracts:
        c.drift_signals = drift_by_contract.get(c.id, [])

    payload: dict[str, Any] = {
        "generated_at": frozen_generated_at or datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo),
        "prework_reality_doc": "'fy'-suites/contractify/state/PREWORK_REPOSITORY_CONTRACT_REALITY.md",
        "governance_scope_doc": "'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md",
        "rollout_limits": {
            "phase1_discovery_contract_ceiling": max_contracts,
            "mature_inventory_soft_ceiling": 200,
            "hard_review_ceiling": 500,
        },
        "automation_policy": {
            "gte_0_90": "may_auto_classify_high_confidence",
            "0_60_to_0_89": "curator_review_required",
            "lt_0_60": "candidate_only_no_auto_anchor",
        },
        "contracts": [serialise(c) for c in contracts],
        "projections": [serialise(p) for p in projections],
        "relations": [serialise(r) for r in relations],
        "drift_findings": [serialise(d) for d in drifts],
        "conflicts": [serialise(c) for c in conflicts],
        "precedence_rules": PRECEDENCE_RULES,
        "adr_governance": adr_governance,
        "runtime_mvp_families": families,
        "manual_unresolved_areas": [serialise(c) for c in spine_conflicts],
        "execution_profile": {"mode": "audit", "max_contracts": max_contracts},
        "actionable_units": build_actionable_units(drifts, conflicts),
        "stats": {
            "n_contracts": len(contracts),
            "n_projections": len(projections),
            "n_relations": len(relations),
            "n_drifts": len(drifts),
            "n_conflicts": len(conflicts),
            "n_manual_unresolved_areas": len(spine_conflicts),
        },
        "disclaimer": "Heuristic drift is evidence for review, not automatic ground truth. "
        "Normative authority outranks observed implementation in governance decisions.",
    }
    return payload


def write_audit_json(
    repo: Path,
    out_path: Path,
    *,
    max_contracts: int = 30,
    frozen_generated_at: str | None = None,
) -> None:
    """Write audit json.

    This callable writes or records artifacts as part of its workflow.

    Args:
        repo: Primary repo used by this step.
        out_path: Filesystem path to the file or directory being
            processed.
        max_contracts: Primary max contracts used by this step.
        frozen_generated_at: Primary frozen generated at used by this
            step.
    """
    payload = run_audit(repo, max_contracts=max_contracts, frozen_generated_at=frozen_generated_at)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
