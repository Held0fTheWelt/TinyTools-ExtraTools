"""Bounded readiness analysis for Diagnosta."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json, write_text

from .evidence import load_supporting_evidence


def _make_warning(
    warning_id: str,
    summary: str,
    *,
    severity: str = "medium",
    visibility_class: str = "visible_non_blocking",
    closure_significance: str = "non_preventive",
) -> dict[str, Any]:
    return {
        "warning_id": warning_id,
        "severity": severity,
        "summary": summary,
        "visibility_class": visibility_class,
        "closure_significance": closure_significance,
    }


def _make_residue(residue_id: str, summary: str, *, severity: str = "medium") -> dict[str, Any]:
    return {"residue_id": residue_id, "severity": severity, "summary": summary}


def _priority_key(item: dict[str, Any]) -> tuple[int, str]:
    order = {"critical": -1, "high": 0, "medium": 1, "low": 2}
    return (order.get(str(item.get("severity") or "medium"), 1), str(item.get("blocker_id") or ""))


def _suite_for_warning(item: dict[str, Any]) -> str:
    warning_id = str(item.get("warning_id") or "")
    parts = warning_id.split(":")
    return parts[1] if len(parts) > 1 else "diagnosta"


def _warning_theme(item: dict[str, Any]) -> str:
    warning_id = str(item.get("warning_id") or "")
    if "proof" in warning_id:
        return "proof_visibility"
    if "hotspot" in warning_id:
        return "structural_visibility"
    if "docker" in warning_id:
        return "environment_visibility"
    if "optional-evidence" in warning_id:
        return "optional_supporting_evidence"
    return "bounded_visibility"


def _build_blocker_clusters(
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    obligation_rows: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    if profile.get("candidate_e_active"):
        raw_items: list[tuple[str, dict[str, Any], str]] = []
        if blockers:
            raw_items.extend(("blocker", item, str(item.get("suite") or "diagnosta")) for item in blockers)
        else:
            raw_items.extend(("warning", item, _suite_for_warning(item)) for item in warnings)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for kind, item, suite in raw_items:
            severity = str(item.get("severity") or "medium")
            grouped[(suite, severity)].append({"kind": kind, **item})
        clusters: list[dict[str, Any]] = []
        ordered_keys = sorted(grouped.keys(), key=lambda key: _priority_key({"severity": key[1], "blocker_id": key[0]}))
        for index, (suite, severity) in enumerate(ordered_keys, 1):
            rows = grouped[(suite, severity)]
            obligation_ids = [
                str(row.get("obligation_id"))
                for row in obligation_rows
                if str(row.get("suite") or "") == suite and row.get("obligation_id")
            ]
            blocker_ids = [str(row.get("blocker_id") or row.get("warning_id") or f"{suite}-item") for row in rows]
            clusters.append(
                {
                    "cluster_id": f"cluster:{suite}:{index}",
                    "suite": suite,
                    "severity": severity,
                    "cluster_kind": "candidate_e_dependency_cluster",
                    "item_count": len(rows),
                    "blocker_ids": blocker_ids,
                    "obligation_ids": obligation_ids,
                    "dependency_targets": [f"cluster:{ordered_keys[index - 2][0]}:{index - 1}"] if index > 1 else [],
                    "review_focus": (
                        f"Deep review cluster for {suite} with {len(rows)} blocker/warning signal(s) and {len(obligation_ids)} linked obligation(s)."
                    ),
                }
            )
        return clusters

    if blockers:
        return [
            {
                "cluster_id": f"cluster:{item['blocker_id']}",
                "suite": item.get("suite", "diagnosta"),
                "severity": item.get("severity", "medium"),
                "cluster_kind": "standard_blocker",
                "item_count": 1,
                "blocker_ids": [item["blocker_id"]],
                "obligation_ids": [],
                "dependency_targets": [],
                "review_focus": item.get("summary", ""),
            }
            for item in sorted(blockers, key=_priority_key)
        ]
    return [
        {
            "cluster_id": "cluster:visibility:1",
            "suite": "diagnosta",
            "severity": "low",
            "cluster_kind": "standard_visibility_cluster",
            "item_count": len(warnings),
            "blocker_ids": [str(item.get("warning_id") or "") for item in warnings],
            "obligation_ids": [],
            "dependency_targets": [],
            "review_focus": "Keep non-blocking visibility explicit while preserving the stable Candidate D lane.",
        }
    ]


def _build_guarantee_gap_clusters(
    blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], residues: list[dict[str, Any]], profile: dict[str, Any]
) -> list[dict[str, Any]]:
    if profile.get("candidate_e_active"):
        grouped: dict[str, dict[str, Any]] = {}
        for item in blockers:
            key = f"blocker:{item.get('suite', 'diagnosta')}"
            grouped.setdefault(
                key,
                {
                    "gap_cluster_id": f"gap:{key}",
                    "gap_family": "blocker_resolution",
                    "suite": item.get("suite", "diagnosta"),
                    "severity": item.get("severity", "medium"),
                    "item_ids": [],
                    "cluster_summary": "",
                },
            )
            grouped[key]["item_ids"].append(item["blocker_id"])
        for item in warnings:
            theme = _warning_theme(item)
            suite = _suite_for_warning(item)
            key = f"warning:{theme}:{suite}"
            grouped.setdefault(
                key,
                {
                    "gap_cluster_id": f"gap:{key}",
                    "gap_family": theme,
                    "suite": suite,
                    "severity": item.get("severity", "medium"),
                    "item_ids": [],
                    "cluster_summary": "",
                },
            )
            grouped[key]["item_ids"].append(item["warning_id"])
        for item in residues:
            key = "residue:bounded"
            grouped.setdefault(
                key,
                {
                    "gap_cluster_id": "gap:residue:bounded",
                    "gap_family": "residue",
                    "suite": "diagnosta",
                    "severity": item.get("severity", "medium"),
                    "item_ids": [],
                    "cluster_summary": "",
                },
            )
            grouped[key]["item_ids"].append(item["residue_id"])
        clusters = []
        for entry in grouped.values():
            entry["cluster_summary"] = (
                f"{entry['gap_family']} cluster for {entry['suite']} with {len(entry['item_ids'])} visible item(s)."
            )
            clusters.append(entry)
        return sorted(clusters, key=lambda item: _priority_key({"severity": item.get("severity"), "blocker_id": item.get("gap_cluster_id")}))

    if blockers:
        return [
            {
                "gap_cluster_id": "gap:standard:blockers",
                "gap_family": "blocker_resolution",
                "suite": "diagnosta",
                "severity": blockers[0].get("severity", "medium"),
                "item_ids": [item["blocker_id"] for item in blockers],
                "cluster_summary": f"Standard blocker gap view with {len(blockers)} blocker(s).",
            }
        ]
    return [
        {
            "gap_cluster_id": "gap:standard:visibility",
            "gap_family": "visibility_only",
            "suite": "diagnosta",
            "severity": "low",
            "item_ids": [str(item.get("warning_id") or "") for item in warnings],
            "cluster_summary": "Standard visibility-only gap view for Candidate D.",
        }
    ]


def _build_next_wave_plan(
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    guarantee_gap_clusters: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    horizon = int(profile.get("planning_horizon") or 1)
    if profile.get("candidate_e_active"):
        plan: list[dict[str, Any]] = []
        for index in range(1, horizon + 1):
            focus_cluster = guarantee_gap_clusters[min(index - 1, len(guarantee_gap_clusters) - 1)] if guarantee_gap_clusters else None
            focus_ids = list((focus_cluster or {}).get("item_ids") or [])[:3]
            plan.append(
                {
                    "wave_id": f"E-wave-{index}",
                    "order": index,
                    "intent": ["stabilize", "prepare", "review"][min(index - 1, 2)],
                    "focus_cluster_id": (focus_cluster or {}).get("gap_cluster_id", "gap:none"),
                    "focus_item_ids": focus_ids,
                    "recommended_action": (
                        f"Candidate E wave {index} should deepen review packets and implementation sequencing for {len(focus_ids)} prioritized item(s)."
                    ),
                    "closure_intent": "review_first_strengthening",
                    "requires_human_review": True,
                }
            )
        return plan

    focus_ids = [item.get("blocker_id") for item in blockers[:1]] or [item.get("warning_id") for item in warnings[:1]]
    return [
        {
            "wave_id": "D-wave-1",
            "order": 1,
            "intent": "single_bounded_next_step",
            "focus_cluster_id": guarantee_gap_clusters[0]["gap_cluster_id"] if guarantee_gap_clusters else "gap:none",
            "focus_item_ids": [item for item in focus_ids if item],
            "recommended_action": "Plan the next bounded review-first step against the highest visible current item.",
            "closure_intent": "bounded_next_step",
            "requires_human_review": True,
        }
    ]


def _build_review_problem_frame(
    blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], profile: dict[str, Any]
) -> dict[str, Any]:
    if profile.get("candidate_e_active"):
        return {
            "frame_id": "review-frame:candidate-e",
            "frame_type": "deep_review_problem_frame",
            "summary": (
                f"Candidate E frames {len(blockers)} blocker(s) and {len(warnings)} warning(s) as a multi-wave review problem with deeper sequencing and packet preparation."
            ),
            "decision_axes": [
                "dependency_order",
                "review_packet_depth",
                "bounded_auto_preparation",
                "residue_honesty",
            ],
        }
    return {
        "frame_id": "review-frame:candidate-d",
        "frame_type": "standard_review_problem_frame",
        "summary": (
            f"Candidate D frames {len(blockers)} blocker(s) and {len(warnings)} warning(s) for the next bounded review-first step."
        ),
        "decision_axes": ["bounded_next_step", "residue_honesty"],
    }


def _build_handoff_packet(
    target_name: str,
    blockers: list[dict[str, Any]],
    priorities: list[dict[str, Any]],
    obligation_rows: list[dict[str, Any]],
    blocker_clusters: list[dict[str, Any]],
    guarantee_gap_clusters: list[dict[str, Any]],
    next_wave_plan: list[dict[str, Any]],
    review_problem_frame: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    grouped_obligations: list[dict[str, Any]] = []
    obligations_by_suite: dict[str, list[str]] = defaultdict(list)
    for item in obligation_rows:
        suite = str(item.get("suite") or "unknown")
        obligation_id = str(item.get("obligation_id") or "")
        if obligation_id:
            obligations_by_suite[suite].append(obligation_id)
    for suite, obligation_ids in sorted(obligations_by_suite.items()):
        grouped_obligations.append(
            {
                "group_id": f"obligation-group:{suite}",
                "suite": suite,
                "obligation_ids": obligation_ids,
                "summary": f"{suite} contributes {len(obligation_ids)} obligation(s) to the closure handoff.",
            }
        )

    if profile.get("candidate_e_active"):
        sequencing_hints = [
            {
                "hint_id": f"seq:{index}",
                "summary": f"Review {cluster['suite']} cluster before wave {min(index + 1, len(next_wave_plan))} packet finalization.",
                "cluster_id": cluster["cluster_id"],
                "wave_id": next_wave_plan[min(index, len(next_wave_plan) - 1)]["wave_id"] if next_wave_plan else "E-wave-1",
            }
            for index, cluster in enumerate(blocker_clusters)
        ]
        return {
            "schema_version": "fy.diagnosta-handoff.v2",
            "handoff_id": f"diagnosta-handoff:{target_name}",
            "depth": profile.get("handoff_depth", "deep_structured"),
            "profile_execution_lane": profile.get("profile_execution_lane"),
            "profile_behavior_depth": profile.get("profile_behavior_depth"),
            "planning_horizon": profile.get("planning_horizon", 3),
            "blocker_clusters": blocker_clusters,
            "guarantee_gap_clusters": guarantee_gap_clusters,
            "grouped_obligations": grouped_obligations,
            "sequencing_hints": sequencing_hints,
            "next_wave_plan": next_wave_plan,
            "review_problem_frame": review_problem_frame,
            "escalation_recommendations": [
                {
                    "escalation_id": f"escalation:{item['blocker_id']}",
                    "blocker_id": item["blocker_id"],
                    "severity": item["severity"],
                    "recommendation": f"Keep {item['suite']} explicit in the next review packet and do not flatten its truth domain.",
                }
                for item in priorities[:3]
            ],
            "review_packet_intent": "deep_review_ready_packet_preparation",
            "closure_rationale": "Candidate E deepens the Diagnosta→Coda handoff without enabling silent auto-apply or suite-truth replacement.",
            "summary": f"Candidate E handoff carries {len(blocker_clusters)} blocker cluster(s), {len(guarantee_gap_clusters)} guarantee-gap cluster(s), and {len(next_wave_plan)} planned wave(s).",
        }

    return {
        "schema_version": "fy.diagnosta-handoff.v1",
        "handoff_id": f"diagnosta-handoff:{target_name}",
        "depth": profile.get("handoff_depth", "standard"),
        "profile_execution_lane": profile.get("profile_execution_lane"),
        "profile_behavior_depth": profile.get("profile_behavior_depth"),
        "planning_horizon": profile.get("planning_horizon", 1),
        "blocker_clusters": blocker_clusters[:1],
        "guarantee_gap_clusters": guarantee_gap_clusters[:1],
        "grouped_obligations": grouped_obligations[:1],
        "sequencing_hints": [],
        "next_wave_plan": next_wave_plan[:1],
        "review_problem_frame": review_problem_frame,
        "escalation_recommendations": [],
        "review_packet_intent": "standard_review_packet_preparation",
        "closure_rationale": "Candidate D keeps the handoff shallow and bounded.",
        "summary": f"Candidate D handoff carries {len(blocker_clusters[:1])} cluster and {len(next_wave_plan[:1])} next step.",
    }


def build_readiness_bundle(workspace: Path, target: Path) -> dict[str, Any]:
    """Build all bounded Diagnosta artifacts for a target workspace."""
    target_id = f"workspace:{target.name}"
    evidence = load_supporting_evidence(workspace)
    profile = evidence["active_strategy_profile"]
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    residues: list[dict[str, Any]] = []
    obligation_rows: list[dict[str, Any]] = []
    evidence_sources = list(evidence.get("evidence_sources") or [])

    primary_suite_count = sum(1 for key in ("contractify", "testify", "despaghettify") if evidence.get(key))
    if primary_suite_count < 2:
        blockers.append(
            {
                "blocker_id": "blocker:diagnosta:insufficient-primary-evidence",
                "suite": "diagnosta",
                "severity": "medium",
                "summary": "Diagnosta lacks enough primary supporting-suite evidence to make a stronger readiness claim.",
                "source_paths": evidence_sources,
            }
        )
        residues.append(
            _make_residue(
                "residue:readiness:abstain-insufficient-primary-evidence",
                "Diagnosta stayed abstain-friendly because fewer than two primary supporting-suite evidence sources were available.",
            )
        )

    contractify = evidence.get("contractify") or {}
    contract_obligations = list(contractify.get("obligations") or [])
    obligation_rows.extend(contract_obligations)
    for item in contract_obligations:
        severity = str(item.get("severity") or "medium")
        if severity in {"high", "medium", "critical"}:
            blockers.append(
                {
                    "blocker_id": f"blocker:contractify:{item.get('obligation_id')}",
                    "suite": "contractify",
                    "severity": severity,
                    "summary": str(item.get("summary") or "Contractify obligation requires review."),
                    "source_paths": list(item.get("source_paths") or []),
                }
            )

    testify = evidence.get("testify") or {}
    proof_status = testify.get("proof_family_status") or {}
    proof_obligations = list(testify.get("obligations") or [])
    obligation_rows.extend(proof_obligations)
    if int(proof_status.get("blocker_gap_count") or 0) > 0:
        blockers.append(
            {
                "blocker_id": "blocker:testify:proof-family-gaps",
                "suite": "testify",
                "severity": str(proof_status.get("highest_blocker_severity") or "medium"),
                "summary": str(proof_status.get("summary") or "Proof-family gaps remain open."),
                "source_paths": [
                    testify.get("written_paths", {}).get(
                        "json_path", "testify/reports/latest_coda_test_obligation_manifest.json"
                    )
                ],
            }
        )
    if int(proof_status.get("warning_gap_count") or 0) > 0:
        warnings.append(
            _make_warning(
                "warning:testify:proof-items",
                f"Testify still reports {proof_status.get('warning_gap_count')} warning-shaped proof item(s).",
            )
        )

    despag = evidence.get("despaghettify") or {}
    hotspot_packet = despag.get("hotspot_decision_packet") or {}
    blocking_hotspots = list(hotspot_packet.get("blocking_hotspots") or [])
    if blocking_hotspots:
        blockers.append(
            {
                "blocker_id": "blocker:despaghettify:local-hotspots",
                "suite": "despaghettify",
                "severity": str(hotspot_packet.get("highest_blocking_severity") or "medium"),
                "summary": str(hotspot_packet.get("summary") or "Local structural hotspots remain."),
                "source_paths": [
                    despag.get("written_paths", {}).get(
                        "json_path", "despaghettify/reports/latest_coda_insertion_surface_report.json"
                    )
                ],
            }
        )
    elif hotspot_packet:
        warnings.append(
            _make_warning(
                "warning:despaghettify:packetized-hotspots",
                "Despaghettify still sees local hotspots, but the remaining burden is packetized and non-blocking for this wave.",
                severity="low",
            )
        )

    dockerify = evidence.get("dockerify") or {}
    docker_warnings = list(dockerify.get("warnings") or [])
    if docker_warnings:
        warnings.append(
            _make_warning(
                "warning:dockerify:warnings",
                f"Dockerify still reports {len(docker_warnings)} warning(s) that remain visible but non-blocking.",
            )
        )

    if not evidence.get("securify"):
        warnings.append(
            _make_warning(
                "warning:readiness:optional-evidence-missing",
                "Optional supporting evidence is still missing: securify.",
            )
        )

    blocker_ids = [item["blocker_id"] for item in sorted(blockers, key=_priority_key)]
    warning_ids = [item["warning_id"] for item in warnings]
    residue_ids = [item["residue_id"] for item in residues]
    readiness_status = "implementation_ready" if not blockers else "not_ready"
    verdict = "bounded_sufficient" if not blockers else "insufficient_for_readiness_claim"
    reason = (
        "No blocker-class evidence remains after bounded synthesis."
        if not blockers
        else f"{len(blockers)} blocker-class signal(s) remain after bounded synthesis."
    )
    cannot_claim = ["full_readiness", "full_closure"] if blockers else ["full_closure"]

    priorities = []
    for item in sorted(blockers, key=_priority_key):
        priorities.append(
            {
                "blocker_id": item["blocker_id"],
                "suite": item["suite"],
                "severity": item["severity"],
                "summary": item["summary"],
                "source_paths": item.get("source_paths") or [],
            }
        )

    blocker_clusters = _build_blocker_clusters(blockers, warnings, obligation_rows, profile)
    guarantee_gap_clusters = _build_guarantee_gap_clusters(blockers, warnings, residues, profile)
    next_wave_plan = _build_next_wave_plan(blockers, warnings, guarantee_gap_clusters, profile)
    review_problem_frame = _build_review_problem_frame(blockers, warnings, profile)
    handoff_packet = _build_handoff_packet(
        target.name,
        blockers,
        priorities,
        obligation_rows,
        blocker_clusters,
        guarantee_gap_clusters,
        next_wave_plan,
        review_problem_frame,
        profile,
    )
    deep_synthesis = {
        "schema_version": "fy.diagnosta-deep-synthesis.v1",
        "synthesis_id": f"deep-synthesis:{target.name}",
        "target_id": target_id,
        "active_profile": profile["active_profile"],
        "profile_execution_lane": profile.get("profile_execution_lane"),
        "profile_behavior_depth": profile.get("profile_behavior_depth"),
        "planning_horizon": profile.get("planning_horizon"),
        "blocker_clusters": blocker_clusters,
        "guarantee_gap_clusters": guarantee_gap_clusters,
        "next_wave_plan": next_wave_plan,
        "review_problem_frame": review_problem_frame,
        "summary": (
            f"Diagnosta {profile['active_profile']} synthesis carries {len(blocker_clusters)} blocker cluster(s), "
            f"{len(guarantee_gap_clusters)} guarantee-gap cluster(s), and planning horizon {profile.get('planning_horizon', 1)}."
        ),
    }

    readiness_case = {
        "schema_version": "fy.readiness-case.v1",
        "readiness_case_id": f"readiness-case:{target.name}",
        "target_id": target_id,
        "target_kind": "workspace",
        "active_profile": profile["active_profile"],
        "profile_execution_lane": profile.get("profile_execution_lane"),
        "profile_behavior_depth": profile.get("profile_behavior_depth"),
        "planning_horizon": profile.get("planning_horizon"),
        "readiness_status": readiness_status,
        "summary": (
            f"Diagnosta readiness case for {target.name} under Candidate {profile['active_profile']} "
            f"with primary evidence coverage {len(evidence_sources)}/3, blocker count {len(blockers)}, "
            f"and planning horizon {profile.get('planning_horizon', 1)}."
        ),
        "blocker_ids": blocker_ids,
        "warning_ids": warning_ids,
        "residue_ids": residue_ids,
        "warnings": warnings,
        "obligation_ids": [str(item.get("obligation_id")) for item in obligation_rows if item.get("obligation_id")],
        "sufficiency_verdict_id": f"sufficiency:{target.name}",
        "cannot_honestly_claim_id": f"cannot-claim:{target.name}",
        "handoff_packet_id": handoff_packet["handoff_id"],
        "deep_synthesis_id": deep_synthesis["synthesis_id"],
        "evidence_sources": evidence_sources,
    }
    blocker_graph = {
        "schema_version": "fy.blocker-graph.v1",
        "blocker_graph_id": f"blocker-graph:{target.name}",
        "target_id": target_id,
        "nodes": blockers,
        "edges": [
            {"from": source, "to": target}
            for cluster in blocker_clusters
            for source in cluster.get("dependency_targets", [])
            for target in [cluster["cluster_id"]]
        ],
        "summary": f"Diagnosta synthesized {len(blockers)} blocker(s) from bounded supporting-suite evidence.",
    }
    blocker_priority_report = {
        "schema_version": "fy.blocker-priority-report.v1",
        "report_id": f"blocker-priority:{target.name}",
        "target_id": target_id,
        "blocker_count": len(priorities),
        "priorities": priorities,
        "summary": f"Prioritized {len(priorities)} blocker(s) for the next bounded wave.",
    }
    obligation_matrix = {
        "schema_version": "fy.obligation-matrix.v1",
        "obligation_matrix_id": f"obligation-matrix:{target.name}",
        "target_id": target_id,
        "rows": obligation_rows,
        "summary": f"Bundled {len(obligation_rows)} supporting obligation row(s) into the readiness review packet.",
    }
    sufficiency_verdict = {
        "schema_version": "fy.sufficiency-verdict.v1",
        "sufficiency_verdict_id": f"sufficiency:{target.name}",
        "target_id": target_id,
        "verdict": verdict,
        "reason": reason,
        "supporting_artifact_paths": evidence_sources,
        "summary": reason,
    }
    cannot_honestly_claim = {
        "schema_version": "fy.cannot-honestly-claim.v1",
        "cannot_honestly_claim_id": f"cannot-claim:{target.name}",
        "target_id": target_id,
        "blocked_claims": cannot_claim,
        "reasons": [item["summary"] for item in priorities] or ["Full closure remains deferred in bounded review-first form."],
        "summary": (
            "Diagnosta blocks strong readiness/closure claims until blocker-class evidence is resolved."
            if blockers
            else "Diagnosta still blocks full closure because bounded review-first closure does not certify full completion."
        ),
    }
    warning_ledger = {
        "schema_version": "fy.warning-ledger.v1",
        "warning_ledger_id": f"warning:{target.name}",
        "target_id": target_id,
        "items": warnings,
        "summary": f"Warnings remain explicit with {len(warnings)} item(s).",
    }
    residue_ledger = {
        "schema_version": "fy.residue-ledger.v1",
        "residue_ledger_id": f"residue:{target.name}",
        "target_id": target_id,
        "items": residues,
        "summary": f"Residue remains explicit with {len(residues)} item(s).",
    }
    guarantee_gap_lines = [
        "# Diagnosta Guarantee Gap Report",
        "",
        readiness_case["summary"],
        "",
        f"- readiness_status: `{readiness_status}`",
        f"- profile_execution_lane: `{profile.get('profile_execution_lane')}`",
        f"- blocker_count: `{len(blockers)}`",
        f"- warning_count: `{len(warnings)}`",
        f"- residue_count: `{len(residues)}`",
        f"- guarantee_gap_cluster_count: `{len(guarantee_gap_clusters)}`",
        f"- planning_horizon: `{profile.get('planning_horizon', 1)}`",
        "",
        "## Blockers",
        "",
    ]
    if priorities:
        for item in priorities:
            guarantee_gap_lines.append(f"- `{item['blocker_id']}` [{item['severity']}] {item['summary']}")
    else:
        guarantee_gap_lines.append("- none")
    guarantee_gap_lines.extend(["", "## Guarantee gap clusters", ""])
    for cluster in guarantee_gap_clusters:
        guarantee_gap_lines.append(
            f"- `{cluster['gap_cluster_id']}` [{cluster.get('severity', 'medium')}] {cluster['cluster_summary']}"
        )
    guarantee_gap_lines.extend(["", "## Next wave plan", ""])
    for item in next_wave_plan:
        guarantee_gap_lines.append(f"- `{item['wave_id']}` {item['recommended_action']}")
    guarantee_gap_lines.extend(["", "## Warnings", ""])
    if warnings:
        for item in warnings:
            guarantee_gap_lines.append(f"- `{item['warning_id']}` [{item['severity']}] {item['summary']}")
    else:
        guarantee_gap_lines.append("- none")
    guarantee_gap_lines.extend(["", "## Residue", ""])
    if residues:
        for item in residues:
            guarantee_gap_lines.append(f"- `{item['residue_id']}` [{item['severity']}] {item['summary']}")
    else:
        guarantee_gap_lines.append("- none")

    return {
        "active_strategy_profile": profile,
        "readiness_case": readiness_case,
        "blocker_graph": blocker_graph,
        "blocker_priority_report": blocker_priority_report,
        "obligation_matrix": obligation_matrix,
        "sufficiency_verdict": sufficiency_verdict,
        "cannot_honestly_claim": cannot_honestly_claim,
        "warning_ledger": warning_ledger,
        "residue_ledger": residue_ledger,
        "deep_synthesis": deep_synthesis,
        "handoff_packet": handoff_packet,
        "guarantee_gap_report": {"markdown": "\n".join(guarantee_gap_lines) + "\n"},
    }


def write_latest_reports(workspace: Path, bundle: dict[str, Any]) -> dict[str, dict[str, str]]:
    reports = workspace / "diagnosta" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    written: dict[str, dict[str, str]] = {}
    for key in [
        "readiness_case",
        "blocker_graph",
        "blocker_priority_report",
        "obligation_matrix",
        "sufficiency_verdict",
        "cannot_honestly_claim",
        "warning_ledger",
        "residue_ledger",
        "deep_synthesis",
        "handoff_packet",
    ]:
        payload = bundle[key]
        json_path = reports / f"latest_{key}.json"
        md_path = reports / f"latest_{key}.md"
        write_json(json_path, payload)
        write_text(md_path, f"# {key.replace('_', ' ').title()}\n\n{payload.get('summary', '')}\n")
        written[key] = {
            "json_path": str(json_path.relative_to(workspace)),
            "md_path": str(md_path.relative_to(workspace)),
        }
    gap_path = reports / "latest_guarantee_gap_report.md"
    write_text(gap_path, bundle["guarantee_gap_report"]["markdown"])
    written["guarantee_gap_report"] = {"md_path": str(gap_path.relative_to(workspace))}
    return written


__all__ = ["build_readiness_bundle", "write_latest_reports"]
