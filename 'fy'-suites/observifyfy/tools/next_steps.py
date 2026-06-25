"""Next-step ranking for observifyfy."""
from __future__ import annotations

from typing import Any


def _priority_from_severity(value: str) -> int:
    return {
        "critical": 98,
        "high": 95,
        "medium": 88,
        "low": 78,
    }.get(str(value).lower(), 80)


def rank_next_steps(
    inventory: dict[str, Any],
    diagnosta_signal: dict[str, Any] | None = None,
    coda_signal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank the next bounded operational actions for observifyfy."""
    actions: list[dict[str, Any]] = []
    for suite in inventory.get("suites", []):
        if not suite.get("exists"):
            continue
        warnings = suite.get("warnings", [])
        if "missing_workflow" in warnings:
            actions.append(
                {
                    "suite": suite["name"],
                    "priority": 90,
                    "reason": "suite has no dedicated CI workflow",
                    "recommended_action": f"Add or repair a workflow for {suite['name']}.",
                }
            )
        if "missing_state" in warnings:
            actions.append(
                {
                    "suite": suite["name"],
                    "priority": 80,
                    "reason": "suite has no visible state file",
                    "recommended_action": f"Create or refresh tracked state for {suite['name']}.",
                }
            )
        if suite.get("run_count", 0) == 0:
            actions.append(
                {
                    "suite": suite["name"],
                    "priority": 70,
                    "reason": "suite has no recorded runs",
                    "recommended_action": (
                        f"Run {suite['name']} at least once and capture evidence."
                    ),
                }
            )
    actions.extend(
        [
            {
                "suite": "contractify",
                "priority": 85,
                "reason": "internal ADR root should be actively governed under docs/ADR",
                "recommended_action": "Keep contractify's internal ADR management discoverable through observifyfy and align references to docs/ADR.",
            },
            {
                "suite": "mvpify",
                "priority": 88,
                "reason": "imported MVP docs should remain mirrored under docs/MVPs/imports and tracked through observifyfy",
                "recommended_action": "Keep mvpify imports normalized and mirrored so temporary implementation folders can be removed safely.",
            },
            {
                "suite": "metrify",
                "priority": 84,
                "reason": "AI usage should remain measured and understandable across suites",
                "recommended_action": "Keep metrify ledgers and reports fresh so AI spend and value stay visible.",
            },
            {
                "suite": "documentify",
                "priority": 85,
                "reason": "internal docs root should be actively governed under docs",
                "recommended_action": "Keep documentify's internal docs management discoverable through observifyfy and align references to docs.",
            },
        ]
    )
    if diagnosta_signal and diagnosta_signal.get("present"):
        readiness_case = diagnosta_signal.get("readiness_case") or {}
        next_wave = diagnosta_signal.get("suggested_next_wave")
        if next_wave:
            actions.append(
                {
                    "suite": next_wave.get("suite", "diagnosta"),
                    "priority": _priority_from_severity(next_wave.get("priority", "medium")),
                    "reason": (
                        f"diagnosta readiness status is {readiness_case.get('readiness_status', 'unknown')}"
                    ),
                    "recommended_action": next_wave.get("recommended_action", "Review Diagnosta blockers."),
                }
            )
        elif readiness_case.get("readiness_status") == "abstain_insufficient_evidence":
            actions.append(
                {
                    "suite": "diagnosta",
                    "priority": 94,
                    "reason": "diagnosta is abstaining because primary evidence is insufficient",
                    "recommended_action": "Collect the missing primary supporting-suite evidence before claiming readiness.",
                }
            )

    if coda_signal and coda_signal.get("present"):
        closure_pack = coda_signal.get("closure_pack") or {}
        closure_movement = coda_signal.get("closure_movement") or {}
        if closure_pack.get("status") == "bounded_partial_closure":
            actions.append(
                {
                    "suite": "coda",
                    "priority": 92,
                    "reason": "closure pack is still partial and residue remains explicit",
                    "recommended_action": "Reduce closure residue by satisfying the next bounded required test/doc or obligation cluster.",
                }
            )
        elif closure_movement.get("residue_count", 0) > 0:
            actions.append(
                {
                    "suite": "coda",
                    "priority": 89,
                    "reason": "closure residue is still present",
                    "recommended_action": "Review the latest Coda residue ledger before making stronger completion claims.",
                }
            )
    actions.sort(key=lambda item: item["priority"], reverse=True)
    return {
        "recommended_next_steps": actions[:12],
        "highest_value_next_step": actions[0] if actions else None,
        "needs_human_decision": [item for item in actions if item["priority"] >= 85],
    }
