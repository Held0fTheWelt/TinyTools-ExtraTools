"""Bounded closure-pack assembly for Coda."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from contractify.tools.coda_exports import emit_contract_obligation_manifest
from despaghettify.tools.coda_exports import emit_insertion_surface_report
from docify.tools.coda_exports import emit_docify_obligation_manifest
from documentify.tools.coda_exports import emit_documentify_obligation_manifest
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from fy_platform.ai.workspace import write_json, write_text
from testify.tools.coda_exports import emit_test_obligation_manifest


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    return _load_json(path) if path.is_file() else None


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


def _dedupe_rows(rows: list[dict[str, Any]], *, primary_key: str, fallback_keys: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        primary = str(row.get(primary_key) or "").strip()
        key = (primary,) if primary else tuple(str(row.get(name) or "").strip() for name in fallback_keys)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _make_review_item(
    item_id: str,
    item_type: str,
    summary: str,
    *,
    source_suite: str,
    adjudication: str,
    source_kind: str = "",
    path: str = "",
    status: str = "accepted_non_blocking",
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "item_type": item_type,
        "summary": summary,
        "source_suite": source_suite,
        "source_kind": source_kind,
        "path": path,
        "status": status,
        "adjudication": adjudication,
    }


def ensure_supporting_exports(workspace: Path) -> dict[str, Any]:
    contractify = emit_contract_obligation_manifest(workspace)
    testify = emit_test_obligation_manifest(workspace)
    despag = emit_insertion_surface_report(workspace)
    docify = None
    documentify = None
    residues: list[dict[str, Any]] = []
    try:
        docify = emit_docify_obligation_manifest(workspace)
    except FileNotFoundError:
        residues.append(
            _make_residue(
                "residue:coda:missing-supporting-export:docify",
                "Docify did not provide a current documentation obligation manifest.",
            )
        )
    try:
        documentify = emit_documentify_obligation_manifest(workspace)
    except FileNotFoundError:
        residues.append(
            _make_residue(
                "residue:coda:missing-supporting-export:documentify",
                "Documentify did not provide a current documentation obligation manifest.",
            )
        )
    return {
        "contractify": contractify,
        "testify": testify,
        "despaghettify": despag,
        "docify": docify,
        "documentify": documentify,
        "residue": residues,
    }


def _adjudicate_tests(required_tests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    open_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for item in required_tests:
        if bool(item.get("blocking")):
            open_items.append(item)
            continue
        review_items.append(
            _make_review_item(
                str(item.get("test_id") or "test-review-item"),
                "test",
                str(item.get("summary") or "Keep bounded test visibility explicit."),
                source_suite=str(item.get("suite") or "testify"),
                source_kind=str(item.get("source_kind") or ""),
                path=str(item.get("workflow_path") or ""),
                adjudication="Visible proof/test follow-up remains review-significant but does not prevent current-target closure.",
            )
        )
    return open_items, review_items


def _adjudicate_docs(required_docs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    open_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for item in required_docs:
        source_kind = str(item.get("source_kind") or "")
        artifact_present = bool(item.get("artifact_present"))
        if source_kind == "generated_document" and artifact_present:
            review_items.append(
                _make_review_item(
                    str(item.get("doc_id") or "doc-review-item"),
                    "doc",
                    str(item.get("summary") or "Keep generated documentation aligned with the closure pack."),
                    source_suite=str(item.get("suite") or "documentify"),
                    source_kind=source_kind,
                    path=str(item.get("path") or ""),
                    adjudication="Generated documentation already exists in current artifacts and remains visible as reviewed supporting material.",
                    status="satisfied_by_current_artifact",
                )
            )
        else:
            open_items.append(item)
    return open_items, review_items


def _adjudicate_obligations(obligations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    open_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for item in obligations:
        if bool(item.get("review_acceptance_candidate")) or bool(item.get("satisfied_by_current_artifacts")):
            review_items.append(
                _make_review_item(
                    str(item.get("obligation_id") or "obligation-review-item"),
                    "obligation",
                    str(item.get("summary") or "Supporting obligation remains visible in reviewed form."),
                    source_suite=str(item.get("suite") or "unknown"),
                    source_kind=str(item.get("category") or ""),
                    path=", ".join(str(p) for p in list(item.get("source_paths") or [])),
                    adjudication="Current artifacts already satisfy the bounded alignment expectation for current-target reviewed closure.",
                    status="review_accepted",
                )
            )
        else:
            open_items.append(item)
    return open_items, review_items


def _group_obligations(open_obligations: list[dict[str, Any]], review_acceptances: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for item in open_obligations:
        key = (str(item.get("suite") or "unknown"), str(item.get("category") or "obligation"))
        group = groups.setdefault(
            key,
            {
                "group_id": f"obligation-group:{key[0]}:{key[1]}",
                "suite": key[0],
                "category": key[1],
                "depth": profile.get("closure_packet_depth", "standard"),
                "open_obligation_ids": [],
                "accepted_review_item_ids": [],
                "summary": "",
            },
        )
        if item.get("obligation_id"):
            group["open_obligation_ids"].append(str(item.get("obligation_id")))
    if profile.get("candidate_e_active"):
        for item in review_acceptances:
            if item.get("item_type") != "obligation":
                continue
            key = (str(item.get("source_suite") or "unknown"), str(item.get("source_kind") or "obligation"))
            group = groups.setdefault(
                key,
                {
                    "group_id": f"obligation-group:{key[0]}:{key[1]}",
                    "suite": key[0],
                    "category": key[1],
                    "depth": profile.get("closure_packet_depth", "standard"),
                    "open_obligation_ids": [],
                    "accepted_review_item_ids": [],
                    "summary": "",
                },
            )
            group["accepted_review_item_ids"].append(str(item.get("item_id") or ""))
    result = []
    for group in groups.values():
        group["summary"] = (
            f"{group['suite']}::{group['category']} carries {len(group['open_obligation_ids'])} open obligation(s) "
            f"and {len(group['accepted_review_item_ids'])} review-accepted obligation item(s)."
        )
        result.append(group)
    return sorted(result, key=lambda item: item["group_id"])


def _build_affected_surface_packets(
    affected_surfaces: list[dict[str, Any]], structural_risks: list[dict[str, Any]], profile: dict[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in affected_surfaces:
        path = str(item.get("path") or item.get("source_path") or "")
        suite = str(item.get("suite") or "unknown")
        key = suite if profile.get("candidate_e_active") else "current-target"
        packet = grouped.setdefault(
            key,
            {
                "packet_id": f"surface-packet:{key}",
                "scope": key,
                "paths": [],
                "risk_ids": [],
                "summary": "",
            },
        )
        if path:
            packet["paths"].append(path)
    for risk in structural_risks:
        scope = str(risk.get("suite") or "unknown") if profile.get("candidate_e_active") else "current-target"
        packet = grouped.setdefault(
            scope,
            {
                "packet_id": f"surface-packet:{scope}",
                "scope": scope,
                "paths": [],
                "risk_ids": [],
                "summary": "",
            },
        )
        if risk.get("risk_id"):
            packet["risk_ids"].append(str(risk.get("risk_id")))
    result = []
    for packet in grouped.values():
        packet["paths"] = sorted(dict.fromkeys(packet["paths"]))
        packet["risk_ids"] = sorted(dict.fromkeys(packet["risk_ids"]))
        packet["summary"] = (
            f"Affected-surface packet for {packet['scope']} with {len(packet['paths'])} path(s) and {len(packet['risk_ids'])} linked risk(s)."
        )
        result.append(packet)
    return sorted(result, key=lambda item: item["packet_id"])


def _build_wave_packets(
    handoff_packet: dict[str, Any] | None,
    grouped_obligations: list[dict[str, Any]],
    affected_surface_packets: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    plan = list((handoff_packet or {}).get("next_wave_plan") or [])
    if not plan:
        plan = [
            {
                "wave_id": "wave-1",
                "recommended_action": "Keep the current closure packet reviewable and residue-honest.",
                "focus_item_ids": [],
            }
        ]
    packets: list[dict[str, Any]] = []
    limit = len(plan) if profile.get("candidate_e_active") else 1
    for index, item in enumerate(plan[:limit], 1):
        packets.append(
            {
                "wave_packet_id": f"closure-wave:{index}",
                "wave_id": item.get("wave_id", f"wave-{index}"),
                "packet_depth": profile.get("closure_packet_depth", "standard"),
                "recommended_action": item.get("recommended_action", "Keep closure work bounded and review-first."),
                "focus_item_ids": list(item.get("focus_item_ids") or []),
                "linked_obligation_groups": [group["group_id"] for group in grouped_obligations[: (2 if profile.get('candidate_e_active') else 1)]],
                "linked_surface_packets": [packet["packet_id"] for packet in affected_surface_packets[: (2 if profile.get('candidate_e_active') else 1)]],
            }
        )
    return packets


def _build_auto_preparation_packets(
    wave_packets: list[dict[str, Any]],
    handoff_packet: dict[str, Any] | None,
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    if not profile.get("candidate_e_active"):
        return []
    packets: list[dict[str, Any]] = []
    for item in wave_packets[:2]:
        packets.append(
            {
                "packet_id": f"auto-prep:{item['wave_packet_id']}",
                "mode": profile.get("bounded_auto_preparation", "review_packet_only"),
                "review_required": True,
                "wave_id": item["wave_id"],
                "prepared_inputs": list(item.get("focus_item_ids") or []),
                "prepared_commands": [
                    "diagnosta diagnose --profile-aware",
                    "coda closure-pack --review-first",
                ],
                "preparation_summary": (
                    f"Prepared a review-ready Candidate E packet for {item['wave_id']} without enabling silent auto-apply."
                ),
                "handoff_depth": (handoff_packet or {}).get("depth", profile.get("handoff_depth", "deep_structured")),
            }
        )
    return packets


def _build_residue_justification(
    residues: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    status: str,
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "justification_id": f"residue-justification:{index}",
            "status": status,
            "profile": profile.get("active_profile", "D"),
            "summary": item.get("summary", ""),
            "classification": "residue" if item.get("residue_id") else "warning",
        }
        for index, item in enumerate(list(residues) + list(warnings), 1)
    ]


def build_closure_bundle(workspace: Path, target: Path) -> dict[str, Any]:
    """Build the bounded closure-pack bundle."""
    profile = strategy_runtime_metadata(workspace)
    supporting = ensure_supporting_exports(workspace)
    readiness_path = workspace / "diagnosta" / "reports" / "latest_readiness_case.json"
    warning_path = workspace / "diagnosta" / "reports" / "latest_warning_ledger.json"
    residue_path = workspace / "diagnosta" / "reports" / "latest_residue_ledger.json"
    handoff_path = workspace / "diagnosta" / "reports" / "latest_handoff_packet.json"
    deep_synthesis_path = workspace / "diagnosta" / "reports" / "latest_deep_synthesis.json"
    readiness_case = _load_optional_json(readiness_path)
    inherited_warnings = list((_load_optional_json(warning_path) or {}).get("items") or [])
    inherited_residue = list((_load_optional_json(residue_path) or {}).get("items") or [])
    handoff_packet = _load_optional_json(handoff_path)
    deep_synthesis = _load_optional_json(deep_synthesis_path)

    obligations = list((supporting["contractify"] or {}).get("obligations") or [])
    obligations.extend(list((supporting["testify"] or {}).get("obligations") or []))
    required_tests = list((supporting["testify"] or {}).get("required_tests") or [])
    required_docs: list[dict[str, Any]] = []
    for key in ["docify", "documentify"]:
        manifest = supporting.get(key) or {}
        required_docs.extend(list(manifest.get("required_docs") or []))
        obligations.extend(list(manifest.get("obligations") or []))

    obligations = _dedupe_rows(obligations, primary_key="obligation_id", fallback_keys=("suite", "summary"))
    required_tests = _dedupe_rows(required_tests, primary_key="test_id", fallback_keys=("suite", "summary"))
    required_docs = _dedupe_rows(required_docs, primary_key="doc_id", fallback_keys=("suite", "path", "summary"))
    affected_surfaces = _dedupe_rows(
        list((supporting["despaghettify"] or {}).get("affected_surfaces") or []),
        primary_key="surface_id",
        fallback_keys=("suite", "path"),
    )
    structural_risks = _dedupe_rows(
        list((supporting["despaghettify"] or {}).get("structural_risks") or []),
        primary_key="risk_id",
        fallback_keys=("suite", "source_path", "summary"),
    )
    hotspot_packet = (supporting["despaghettify"] or {}).get("hotspot_decision_packet") or {}

    warnings = list(inherited_warnings)
    residues = list(supporting["residue"]) + inherited_residue
    if hotspot_packet and hotspot_packet.get("blocking_hotspots"):
        residues.append(
            _make_residue(
                "residue:coda:hotspots-still-open",
                "Structural hotspots remain explicit inside the closure pack.",
            )
        )

    readiness_is_implementation_ready = bool(readiness_case) and readiness_case.get("readiness_status") == "implementation_ready"
    if not readiness_is_implementation_ready:
        residues.append(
            _make_residue(
                "residue:coda:closure-not-ready",
                "Full closure is not honestly justified while Diagnosta does not yet report implementation_ready.",
            )
        )

    open_required_tests, accepted_test_items = _adjudicate_tests(required_tests)
    open_required_docs, accepted_doc_items = _adjudicate_docs(required_docs)
    open_obligations, accepted_obligation_items = _adjudicate_obligations(obligations)

    warnings = _dedupe_rows(warnings, primary_key="warning_id", fallback_keys=("summary",))
    residues = _dedupe_rows(residues, primary_key="residue_id", fallback_keys=("summary",))
    review_acceptances = _dedupe_rows(
        accepted_test_items + accepted_doc_items + accepted_obligation_items,
        primary_key="item_id",
        fallback_keys=("item_type", "summary"),
    )

    if residues or not readiness_is_implementation_ready:
        status = "bounded_partial_closure"
    elif open_obligations or open_required_tests or open_required_docs:
        status = "bounded_review_ready"
    else:
        status = "closed_for_current_target_reviewed_scope"

    grouped_obligations = _group_obligations(open_obligations, review_acceptances, profile)
    affected_surface_packets = _build_affected_surface_packets(affected_surfaces, structural_risks, profile)
    wave_packets = _build_wave_packets(handoff_packet, grouped_obligations, affected_surface_packets, profile)
    auto_preparation_packets = _build_auto_preparation_packets(wave_packets, handoff_packet, profile)
    residue_justification = _build_residue_justification(residues, warnings, status, profile)

    target_id = f"workspace:{target.name}"
    review_sections = [
        {"section_id": "problem-frame", "title": "Problem frame", "summary": ((deep_synthesis or {}).get("review_problem_frame") or {}).get("summary", "Bounded review-first closure packet.")},
        {"section_id": "warning-ledger", "title": "Visible warnings", "summary": f"{len(warnings)} warning item(s) remain visible and non-blocking."},
    ]
    if profile.get("candidate_e_active"):
        review_sections.extend(
            [
                {"section_id": "grouped-obligations", "title": "Grouped obligations", "summary": f"{len(grouped_obligations)} grouped obligation packet(s)."},
                {"section_id": "wave-packets", "title": "Wave packets", "summary": f"{len(wave_packets)} multi-wave packet(s) prepared."},
                {"section_id": "auto-preparation", "title": "Bounded auto-preparation", "summary": f"{len(auto_preparation_packets)} review-ready preparation packet(s)."},
            ]
        )

    review_packet = {
        "schema_version": "fy.review-packet.v1",
        "review_packet_id": f"review-packet:{target.name}",
        "target_id": target_id,
        "status": status,
        "packet_depth": profile.get("review_packet_depth", "standard"),
        "profile_execution_lane": profile.get("profile_execution_lane"),
        "warnings": warnings,
        "accepted_items": review_acceptances,
        "remaining_open_items": {
            "obligations": open_obligations,
            "required_tests": open_required_tests,
            "required_docs": open_required_docs,
        },
        "grouped_obligations": grouped_obligations,
        "wave_packets": wave_packets,
        "auto_preparation_packets": auto_preparation_packets,
        "sections": review_sections,
        "decision_summary": (
            "Current-target reviewed closure is honest: no blocker-class or residue-class burden remains, and remaining visible items are review-accepted or warning-only."
            if status == "closed_for_current_target_reviewed_scope"
            else "Bounded review remains required because open review burdens are still attached to the closure pack."
        ),
        "accepted_non_blocking_visibility": [item["warning_id"] for item in warnings],
    }
    closure_pack = {
        "schema_version": "fy.closure-pack.v2" if profile.get("candidate_e_active") else "fy.closure-pack.v1",
        "closure_pack_id": f"closure-pack:{target.name}",
        "target_id": target_id,
        "active_profile": profile["active_profile"],
        "profile_execution_lane": profile.get("profile_execution_lane"),
        "profile_behavior_depth": profile.get("profile_behavior_depth"),
        "packet_depth": profile.get("closure_packet_depth", "standard"),
        "planning_horizon": profile.get("planning_horizon", 1),
        "status": status,
        "review_required": True,
        "obligation_ids": [str(item.get("obligation_id")) for item in open_obligations if item.get("obligation_id")],
        "accepted_obligation_ids": [item["item_id"] for item in accepted_obligation_items],
        "warning_ids": [item["warning_id"] for item in warnings],
        "residue_ids": [item["residue_id"] for item in residues],
        "warnings": warnings,
        "obligations": open_obligations,
        "required_tests": open_required_tests,
        "required_docs": open_required_docs,
        "review_acceptances": review_acceptances,
        "review_packet_id": review_packet["review_packet_id"],
        "affected_surfaces": affected_surfaces,
        "affected_surface_packets": affected_surface_packets,
        "structural_risks": structural_risks,
        "grouped_obligations": grouped_obligations,
        "wave_packets": wave_packets,
        "auto_preparation_packets": auto_preparation_packets,
        "residue_justification": residue_justification,
        "handoff_packet_id": (handoff_packet or {}).get("handoff_id", ""),
        "justification": [
            "Coda only assembles bounded review-first closure packs.",
            "Supporting-suite truth remains owned by the originating suites.",
            "Warnings stay visible without being overstated as residue.",
            "Already-generated docs and non-blocking test items can be review-accepted without pretending they disappeared.",
            "Residue stays explicit whenever stronger closure is not justified.",
            "Candidate E deepens packet shaping without enabling silent auto-apply." if profile.get("candidate_e_active") else "Candidate D keeps packet shaping intentionally shallow.",
        ],
        "summary": (
            f"Coda assembled a {profile.get('profile_behavior_depth', 'standard')} closure pack for {target.name} with {len(open_obligations)} open obligation(s), "
            f"{len(open_required_tests)} open required test item(s), {len(open_required_docs)} open required doc item(s), "
            f"{len(review_acceptances)} review-accepted item(s), {len(warnings)} warning item(s), {len(residues)} residue item(s), and {len(wave_packets)} wave packet(s)."
        ),
        "source_reports": {
            "contractify": (supporting["contractify"] or {}).get("written_paths", {}).get("json_path", "contractify/reports/latest_coda_obligation_manifest.json"),
            "testify": (supporting["testify"] or {}).get("written_paths", {}).get("json_path", "testify/reports/latest_coda_test_obligation_manifest.json"),
            "despaghettify": (supporting["despaghettify"] or {}).get("written_paths", {}).get("json_path", "despaghettify/reports/latest_coda_insertion_surface_report.json"),
            "docify": ((supporting.get("docify") or {}).get("written_paths", {}) or {}).get("json_path", ""),
            "documentify": ((supporting.get("documentify") or {}).get("written_paths", {}) or {}).get("json_path", ""),
            "readiness_case": str(readiness_path.relative_to(workspace)) if readiness_path.is_file() else "",
            "diagnosta_handoff": str(handoff_path.relative_to(workspace)) if handoff_path.is_file() else "",
            "diagnosta_deep_synthesis": str(deep_synthesis_path.relative_to(workspace)) if deep_synthesis_path.is_file() else "",
        },
    }
    warning_ledger = {
        "schema_version": "fy.warning-ledger.v1",
        "warning_ledger_id": f"coda-warning:{target.name}",
        "target_id": target_id,
        "items": warnings,
        "summary": f"Coda keeps {len(warnings)} warning item(s) explicit.",
    }
    residue_ledger = {
        "schema_version": "fy.residue-ledger.v1",
        "residue_ledger_id": f"coda-residue:{target.name}",
        "target_id": target_id,
        "items": residues,
        "summary": f"Coda keeps {len(residues)} residue item(s) explicit.",
    }
    return {
        "active_strategy_profile": profile,
        "readiness_case": readiness_case,
        "diagnosta_handoff": handoff_packet,
        "diagnosta_deep_synthesis": deep_synthesis,
        "closure_pack": closure_pack,
        "warning_ledger": warning_ledger,
        "residue_ledger": residue_ledger,
        "review_packet": review_packet,
    }


def write_latest_reports(workspace: Path, bundle: dict[str, Any]) -> dict[str, dict[str, str]]:
    reports = workspace / "coda" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    closure_json = reports / "latest_closure_pack.json"
    closure_md = reports / "latest_closure_pack.md"
    warning_json = reports / "latest_warning_ledger.json"
    warning_md = reports / "latest_warning_ledger.md"
    residue_json = reports / "latest_residue_ledger.json"
    residue_md = reports / "latest_residue_ledger.md"
    review_json = reports / "latest_review_packet.json"
    review_md = reports / "latest_review_packet.md"
    write_json(closure_json, bundle["closure_pack"])
    write_text(closure_md, "# Coda Closure Pack\n\n" + bundle["closure_pack"]["summary"] + "\n")
    write_json(warning_json, bundle["warning_ledger"])
    write_text(warning_md, "# Coda Warning Ledger\n\n" + bundle["warning_ledger"]["summary"] + "\n")
    write_json(residue_json, bundle["residue_ledger"])
    write_text(residue_md, "# Coda Residue Ledger\n\n" + bundle["residue_ledger"]["summary"] + "\n")
    write_json(review_json, bundle["review_packet"])
    write_text(review_md, "# Coda Review Packet\n\n" + bundle["review_packet"]["decision_summary"] + "\n")
    return {
        "closure_pack": {
            "json_path": str(closure_json.relative_to(workspace)),
            "md_path": str(closure_md.relative_to(workspace)),
        },
        "warning_ledger": {
            "json_path": str(warning_json.relative_to(workspace)),
            "md_path": str(warning_md.relative_to(workspace)),
        },
        "residue_ledger": {
            "json_path": str(residue_json.relative_to(workspace)),
            "md_path": str(residue_md.relative_to(workspace)),
        },
        "review_packet": {
            "json_path": str(review_json.relative_to(workspace)),
            "md_path": str(review_md.relative_to(workspace)),
        },
    }


__all__ = ["build_closure_bundle", "ensure_supporting_exports", "write_latest_reports"]
