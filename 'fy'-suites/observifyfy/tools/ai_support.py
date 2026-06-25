"""AI support helpers for observifyfy."""
from __future__ import annotations

from typing import Any


def build_ai_context(
    inventory: dict[str, Any],
    next_steps: dict[str, Any],
    diagnosta_signal: dict[str, Any] | None = None,
    coda_signal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build AI-readable cross-suite operational context."""
    suites = inventory.get("suites", [])
    focus = [
        {
            "suite": item["name"],
            "warnings": item.get("warnings", []),
            "run_count": item.get("run_count", 0),
            "journal_count": item.get("journal_count", 0),
        }
        for item in suites
        if item.get("exists")
    ]
    context: dict[str, Any] = {
        "purpose": "AI-readable cross-suite operational context for fy-suite self-management.",
        "managed_internal_roots": inventory.get("internal_roots", {}),
        "suite_focus": focus,
        "next_steps": next_steps.get("recommended_next_steps", []),
        "search_hints": [
            "suite health",
            "freshness",
            "cross-suite conflicts",
            "contractify internal ADR management",
            "documentify internal docs management",
            "status pages",
            "run journals",
            "mvpify imported MVP mirroring",
            "metrify cost and usage summaries",
            "diagnosta readiness cases",
            "diagnosta blocker graphs",
            "coda closure packs",
            "coda residue ledgers",
        ],
        "memory_contract": {
            "store": "observifyfy tracks suite operations memory, not project-facing truth",
            "refresh_rule": "prefer latest run evidence and internal docs over stale summaries",
            "guardrails": [
                "do_not_overwrite_project_truth",
                "do_not_flatten_contractify_or_testify_findings",
            ],
        },
    }
    if diagnosta_signal and diagnosta_signal.get("present"):
        readiness_case = diagnosta_signal.get("readiness_case") or {}
        blocker_priority_report = diagnosta_signal.get("blocker_priority_report") or {}
        depth = diagnosta_signal.get("profile_depth_signal") or {}
        context["diagnosta"] = {
            "active_profile": ((diagnosta_signal.get("active_strategy_profile") or {}).get("active_profile", "D")),
            "readiness_status": readiness_case.get("readiness_status", "unknown"),
            "blocker_count": len(blocker_priority_report.get("priorities") or []),
            "warning_count": len(readiness_case.get("warnings") or []),
            "profile_execution_lane": depth.get("profile_execution_lane"),
            "profile_behavior_depth": depth.get("profile_behavior_depth"),
            "blocker_cluster_count": depth.get("blocker_cluster_count", 0),
            "guarantee_gap_cluster_count": depth.get("guarantee_gap_cluster_count", 0),
            "next_wave_count": depth.get("next_wave_count", 0),
            "handoff_depth": depth.get("handoff_depth", "standard"),
            "suggested_next_wave": diagnosta_signal.get("suggested_next_wave"),
        }

    if coda_signal and coda_signal.get("present"):
        closure_pack = coda_signal.get("closure_pack") or {}
        closure_movement = coda_signal.get("closure_movement") or {}
        context["coda"] = {
            "active_profile": ((coda_signal.get("active_strategy_profile") or {}).get("active_profile", "D")),
            "closure_status": closure_pack.get("status", "unknown"),
            "obligation_count": closure_movement.get("obligation_count", 0),
            "required_test_count": closure_movement.get("required_test_count", 0),
            "required_doc_count": closure_movement.get("required_doc_count", 0),
            "warning_count": closure_movement.get("warning_count", 0),
            "residue_count": closure_movement.get("residue_count", 0),
            "grouped_obligation_count": closure_movement.get("grouped_obligation_count", 0),
            "wave_packet_count": closure_movement.get("wave_packet_count", 0),
            "auto_preparation_count": closure_movement.get("auto_preparation_count", 0),
            "packet_depth": closure_movement.get("packet_depth", "standard"),
        }
    return context


def build_llms_txt(ai_context: dict[str, Any]) -> str:
    """Render a compact LLM-facing text summary for observifyfy reports."""
    lines = [
        "# Observifyfy LLM Context",
        "",
        ai_context.get("purpose", ""),
        "",
    ]
    diagnosta = ai_context.get("diagnosta") or {}
    if diagnosta:
        lines.extend(
            [
                "## Diagnosta",
                f"- active_profile: {diagnosta.get('active_profile', 'D')}",
                f"- readiness_status: {diagnosta.get('readiness_status', 'unknown')}",
                f"- blocker_count: {diagnosta.get('blocker_count', 0)}",
                f"- warning_count: {diagnosta.get('warning_count', 0)}",
                "",
            ]
        )
    coda = ai_context.get("coda") or {}
    if coda:
        lines.extend(
            [
                "## Coda",
                f"- active_profile: {coda.get('active_profile', 'D')}",
                f"- closure_status: {coda.get('closure_status', 'unknown')}",
                f"- obligation_count: {coda.get('obligation_count', 0)}",
                f"- required_test_count: {coda.get('required_test_count', 0)}",
                f"- required_doc_count: {coda.get('required_doc_count', 0)}",
                f"- warning_count: {coda.get('warning_count', 0)}",
                f"- residue_count: {coda.get('residue_count', 0)}",
                "",
            ]
        )
    lines.append("## Next steps")
    for item in ai_context.get("next_steps", [])[:10]:
        lines.append(f"- {item.get('suite', 'unknown')}: {item.get('recommended_action', '')}")
    lines.append("")
    return "\n".join(lines) + "\n"
