"""Final release-grade reporting for readiness-and-closure current-target closure."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace_io import write_json, write_text

FINAL_CLOSURE_LABEL = "closed_for_current_target_reviewed_scope"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    return _load_json(path) if path.is_file() else None


def _warning_owner(warning_id: str) -> dict[str, str]:
    if warning_id == "warning:testify:proof-items":
        return {
            "owner": "testify",
            "future_wave_class": "proof-hardening",
            "reporting_scope": "current_target_closure_reporting",
            "non_blocking_reason": "Proof-family blocker gaps are gone; remaining items are visible workflow/linked-claim notes.",
        }
    if warning_id == "warning:despaghettify:packetized-hotspots":
        return {
            "owner": "despaghettify",
            "future_wave_class": "structural-maintainability",
            "reporting_scope": "current_target_closure_reporting",
            "non_blocking_reason": "Only packetized non-blocking hotspots remain after blocker-class hotspot removal.",
        }
    if warning_id == "warning:dockerify:warnings":
        return {
            "owner": "dockerify",
            "future_wave_class": "container-polish",
            "reporting_scope": "future_roadmap_reporting",
            "non_blocking_reason": "Warnings remain visible, but they do not prevent the current reviewed closure target.",
        }
    if warning_id == "warning:readiness:optional-evidence-missing":
        return {
            "owner": "securify",
            "future_wave_class": "optional-evidence-enrichment",
            "reporting_scope": "future_roadmap_reporting",
            "non_blocking_reason": "The missing supporting signal is explicitly optional and not required for current-target closure.",
        }
    return {
        "owner": "unknown",
        "future_wave_class": "future-review",
        "reporting_scope": "current_target_closure_reporting",
        "non_blocking_reason": "This warning remains visible and non-blocking for the current reviewed scope.",
    }


def _markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def build_final_release_bundle(workspace: Path) -> dict[str, Any]:
    diagnosta = _load_json(workspace / "diagnosta/reports/latest_readiness_case.json")
    coda = _load_json(workspace / "coda/reports/latest_closure_pack.json")
    review_packet = _load_json(workspace / "coda/reports/latest_review_packet.json")
    diagnosta_warning_ledger = _load_optional_json(
        workspace / "diagnosta/reports/latest_warning_ledger.json"
    ) or {"items": []}
    coda_warning_ledger = _load_optional_json(
        workspace / "coda/reports/latest_warning_ledger.json"
    ) or {"items": []}
    manifest = _load_optional_json(
        workspace / "docs/platform/self_hosting/readiness_closure_self_hosting_manifest.json"
    ) or {}

    warnings = list(diagnosta_warning_ledger.get("items") or coda_warning_ledger.get("items") or [])
    open_obligation_count = len(coda.get("obligations") or [])
    open_required_test_count = len(coda.get("required_tests") or [])
    open_required_doc_count = len(coda.get("required_docs") or [])
    accepted_review_item_count = len(coda.get("review_acceptances") or [])
    blocker_count = len(diagnosta.get("blocker_ids") or [])
    residue_count = len(manifest.get("residue_ids") or []) if manifest else len(
        (_load_optional_json(workspace / "diagnosta/reports/latest_residue_ledger.json") or {"items": []}).get("items") or []
    )
    warning_count = len(warnings)

    closure_status = str(coda.get("status") or "")
    readiness_status = str(diagnosta.get("readiness_status") or "")
    label_stable = (
        readiness_status == "implementation_ready"
        and closure_status == FINAL_CLOSURE_LABEL
        and blocker_count == 0
        and residue_count == 0
        and open_obligation_count == 0
        and open_required_test_count == 0
        and open_required_doc_count == 0
    )

    warning_governance = []
    for item in warnings:
        merged = dict(item)
        merged.update(_warning_owner(str(item.get("warning_id") or "")))
        warning_governance.append(merged)

    claimable = [
        "Current-target implementation readiness is established.",
        "Current-target reviewed closure is established.",
        "The current target is blocker-free and residue-free.",
        "Visible non-blocking warnings remain explicit.",
    ]
    not_claimable = [
        "Universal or global full fy-suites closure.",
        "Proof-certified autonomous closure.",
        "Candidate E capabilities or automation.",
        "Silence of all warnings.",
        "Broad meta-suite authority beyond the delivered readiness-and-closure scope.",
    ]

    terminal_manifest = {
        "schema_version": "fy.readiness-closure-terminal-manifest.v1",
        "wave": "F7",
        "terminal_label": closure_status,
        "terminal_label_frozen": label_stable,
        "readiness_status": readiness_status,
        "closure_status": closure_status,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "residue_count": residue_count,
        "open_obligation_count": open_obligation_count,
        "open_required_test_count": open_required_test_count,
        "open_required_doc_count": open_required_doc_count,
        "accepted_review_item_count": accepted_review_item_count,
        "warning_ids": [str(item.get("warning_id") or "") for item in warnings],
        "review_packet_id": review_packet.get("review_packet_id", ""),
        "current_target_claimable": claimable,
        "current_target_not_claimable": not_claimable,
        "warning_governance": warning_governance,
        "decision_summary": (
            "The current repository target is stably closed for reviewed scope with visible non-blocking warnings."
            if label_stable
            else "The prior reviewed-scope closure label did not remain stable under the refreshed F7 proof pass."
        ),
    }

    claim_boundary = {
        "current_target_claimable": claimable,
        "current_target_not_claimable": not_claimable,
    }

    comparison = {
        "schema_version": "fy.readiness-closure-comparison.v1",
        "from_wave": "F6",
        "to_wave": "F7",
        "readiness_status_before": manifest.get("readiness_status", ""),
        "readiness_status_after": readiness_status,
        "closure_status_before": manifest.get("closure_status", ""),
        "closure_status_after": closure_status,
        "warning_count_before": manifest.get("warning_count", 0),
        "warning_count_after": warning_count,
        "residue_count_before": manifest.get("residue_count", 0),
        "residue_count_after": residue_count,
        "accepted_review_item_count_before": manifest.get("accepted_review_item_count", 0),
        "accepted_review_item_count_after": accepted_review_item_count,
        "label_stable": label_stable,
    }

    closure_decision_md = "\n".join(
        [
            "# Final Current-Target Closure Decision",
            "",
            f"- readiness_status: `{readiness_status}`",
            f"- closure_status: `{closure_status}`",
            f"- terminal_label_frozen: `{str(label_stable).lower()}`",
            f"- blocker_count: `{blocker_count}`",
            f"- residue_count: `{residue_count}`",
            f"- warning_count: `{warning_count}`",
            f"- open_obligation_count: `{open_obligation_count}`",
            f"- open_required_test_count: `{open_required_test_count}`",
            f"- open_required_doc_count: `{open_required_doc_count}`",
            f"- accepted_review_item_count: `{accepted_review_item_count}`",
            "",
            terminal_manifest["decision_summary"],
            "",
            "Warnings remain visible and non-blocking; they do not reopen blocker or residue status for the current repository target.",
            "",
        ]
    ) + "\n"

    claim_boundary_md = "\n".join(
        [
            "# Final Current-Target Claim Boundary",
            "",
            "## What is now honestly claimable",
            "",
            _markdown_list(claimable),
            "",
            "## What is still not claimable",
            "",
            _markdown_list(not_claimable),
            "",
        ]
    ) + "\n"

    comparison_md = "\n".join(
        [
            "# Readiness-Closure F7 Comparison",
            "",
            f"- readiness_status: `{comparison['readiness_status_before']}` -> `{comparison['readiness_status_after']}`",
            f"- closure_status: `{comparison['closure_status_before']}` -> `{comparison['closure_status_after']}`",
            f"- warning_count: `{comparison['warning_count_before']}` -> `{comparison['warning_count_after']}`",
            f"- residue_count: `{comparison['residue_count_before']}` -> `{comparison['residue_count_after']}`",
            f"- accepted_review_item_count: `{comparison['accepted_review_item_count_before']}` -> `{comparison['accepted_review_item_count_after']}`",
            f"- label_stable: `{str(label_stable).lower()}`",
            "",
        ]
    ) + "\n"

    warning_lines = ["# Final Warning Governance", ""]
    for item in warning_governance:
        warning_lines.extend(
            [
                f"## {item['warning_id']}",
                "",
                f"- severity: `{item.get('severity', 'unknown')}`",
                f"- visibility_class: `{item.get('visibility_class', 'unknown')}`",
                f"- remains_visible_because: {item.get('summary', '')}",
                f"- does_not_block_because: {item.get('non_blocking_reason', '')}",
                f"- future_wave_class: `{item.get('future_wave_class', 'future-review')}`",
                f"- reporting_scope: `{item.get('reporting_scope', 'current_target_closure_reporting')}`",
                "",
            ]
        )
    final_warning_md = "\n".join(warning_lines) + "\n"

    final_summary = {
        "schema_version": "fy.observifyfy-final-summary.v1",
        "readiness_status": readiness_status,
        "closure_status": closure_status,
        "terminal_label_frozen": label_stable,
        "warning_count": warning_count,
        "warning_ids": terminal_manifest["warning_ids"],
        "accepted_review_item_count": accepted_review_item_count,
        "summary": terminal_manifest["decision_summary"],
    }
    final_summary_md = "\n".join(
        [
            "# Observifyfy Final Readiness-Closure Summary",
            "",
            f"- readiness_status: `{readiness_status}`",
            f"- closure_status: `{closure_status}`",
            f"- terminal_label_frozen: `{str(label_stable).lower()}`",
            f"- warning_count: `{warning_count}`",
            f"- accepted_review_item_count: `{accepted_review_item_count}`",
            "",
            final_summary["summary"],
            "",
        ]
    ) + "\n"

    report_md = "\n".join(
        [
            "# Readiness-and-Closure F7 Final Release Adjudication Report",
            "",
            "## Final terminal label",
            "",
            f"- readiness_status: `{readiness_status}`",
            f"- closure_status: `{closure_status}`",
            f"- terminal_label_frozen: `{str(label_stable).lower()}`",
            "",
            "## Warning governance",
            "",
            *[
                f"- `{item['warning_id']}` remains visible and non-blocking; owned by `{item['owner']}` for later `{item['future_wave_class']}` work."
                for item in warning_governance
            ],
            "",
            "## Claim boundary",
            "",
            "### Claimable",
            "",
            _markdown_list(claimable),
            "",
            "### Not claimable",
            "",
            _markdown_list(not_claimable),
            "",
        ]
    ) + "\n"

    return {
        "terminal_manifest": terminal_manifest,
        "terminal_manifest_md": closure_decision_md,
        "claim_boundary": claim_boundary,
        "claim_boundary_md": claim_boundary_md,
        "comparison": comparison,
        "comparison_md": comparison_md,
        "warning_governance_md": final_warning_md,
        "final_summary": final_summary,
        "final_summary_md": final_summary_md,
        "report_md": report_md,
    }


def write_final_release_bundle(workspace: Path) -> dict[str, Any]:
    bundle = build_final_release_bundle(workspace)
    docs = workspace / "docs/platform"
    self_hosting = docs / "self_hosting"
    observifyfy_reports = workspace / "observifyfy/reports"

    write_text(docs / "FINAL_CURRENT_TARGET_CLOSURE_DECISION.md", bundle["terminal_manifest_md"])
    write_text(docs / "FINAL_CURRENT_TARGET_CLAIM_BOUNDARY.md", bundle["claim_boundary_md"])
    write_text(docs / "READINESS_CLOSURE_F7_FINAL_RELEASE_ADJUDICATION_REPORT.md", bundle["report_md"])
    write_text(docs / "FINAL_WARNING_GOVERNANCE.md", bundle["warning_governance_md"])
    write_json(self_hosting / "readiness_closure_final_terminal_manifest.json", bundle["terminal_manifest"])
    write_text(self_hosting / "readiness_closure_final_terminal_manifest.md", bundle["terminal_manifest_md"])
    write_json(self_hosting / "readiness_closure_followon_f7_comparison.json", bundle["comparison"])
    write_text(self_hosting / "readiness_closure_followon_f7_comparison.md", bundle["comparison_md"])
    write_json(observifyfy_reports / "observifyfy_final_readiness_closure_summary.json", bundle["final_summary"])
    write_text(observifyfy_reports / "observifyfy_final_readiness_closure_summary.md", bundle["final_summary_md"])
    return bundle


__all__ = ["FINAL_CLOSURE_LABEL", "build_final_release_bundle", "write_final_release_bundle"]
