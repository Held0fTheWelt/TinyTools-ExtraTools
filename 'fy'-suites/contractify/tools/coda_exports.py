"""Coda-facing export surfaces for Contractify.

This module derives a bounded obligation manifest from existing Contractify
reports. It does not create new contract truth. It only packages already
observed drift, conflict, and unresolved-boundary signals into a form that
Coda can attach to closure packs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, write_json, write_text

_REPORT_CANDIDATES = (
    Path("contractify/reports/audit_latest.json"),
    Path("contractify/reports/contract_audit.json"),
    Path("contractify/reports/_local_contract_audit.json"),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _first_existing(workspace: Path) -> Path:
    for rel in _REPORT_CANDIDATES:
        path = workspace / rel
        if path.is_file():
            return path
    raise FileNotFoundError("No supported Contractify audit report was found.")


def _append_obligation(
    obligations: list[dict[str, Any]],
    *,
    obligation_id: str,
    category: str,
    severity: str,
    summary: str,
    source_paths: list[str],
) -> None:
    obligations.append(
        {
            "obligation_id": obligation_id,
            "suite": "contractify",
            "category": category,
            "severity": severity,
            "summary": summary,
            "source_paths": source_paths,
            "review_required": True,
        }
    )


def build_contract_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Build a bounded Contractify obligation manifest for Coda."""
    report_path = _first_existing(workspace)
    report = _load_json(report_path)
    obligations: list[dict[str, Any]] = []

    for item in list(report.get("drift_findings") or [])[:8]:
        _append_obligation(
            obligations,
            obligation_id=str(item.get("id") or f"contractify-drift-{len(obligations)+1}"),
            category="contract_drift",
            severity=str(item.get("severity") or "medium"),
            summary=str(item.get("summary") or "Resolve a Contractify drift finding."),
            source_paths=[str(path) for path in list(item.get("evidence_sources") or [])[:6]],
        )
    for item in list(report.get("conflicts") or [])[:8]:
        _append_obligation(
            obligations,
            obligation_id=str(item.get("id") or f"contractify-conflict-{len(obligations)+1}"),
            category="contract_conflict",
            severity=str(item.get("severity") or "medium"),
            summary=str(item.get("summary") or "Review a Contractify conflict."),
            source_paths=[str(path) for path in list(item.get("sources") or [])[:6]],
        )
    for item in list(report.get("manual_unresolved_areas") or [])[:6]:
        _append_obligation(
            obligations,
            obligation_id=str(item.get("id") or f"contractify-unresolved-{len(obligations)+1}"),
            category="intentional_unresolved_boundary",
            severity=str(item.get("severity") or "medium"),
            summary=str(
                item.get("summary")
                or "Review an intentionally unresolved Contractify boundary."
            ),
            source_paths=[str(path) for path in list(item.get("sources") or [])[:6]],
        )

    actionable_units = [str(item) for item in list(report.get("actionable_units") or [])[:12]]
    manifest = {
        "schema_version": "fy.contractify-coda-obligation-manifest.v1",
        "suite": "contractify",
        "generated_at": utc_now(),
        "source_report": str(report_path.relative_to(workspace)),
        "obligations": obligations,
        "actionable_units": actionable_units,
        "summary": (
            f"Contractify exported {len(obligations)} bounded closure obligations "
            f"from drift, conflict, and unresolved-boundary evidence."
        ),
    }
    return manifest


def emit_contract_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Write the latest Contractify obligation manifest for Coda."""
    manifest = build_contract_obligation_manifest(workspace)
    reports = workspace / "contractify" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest_coda_obligation_manifest.json"
    md_path = reports / "latest_coda_obligation_manifest.md"
    write_json(json_path, manifest)
    lines = [
        "# Contractify Coda Obligation Manifest",
        "",
        manifest["summary"],
        "",
        f"- source_report: `{manifest['source_report']}`",
        f"- obligation_count: `{len(manifest['obligations'])}`",
        "",
        "## Obligations",
        "",
    ]
    if manifest["obligations"]:
        for item in manifest["obligations"]:
            lines.append(
                f"- `{item['obligation_id']}` [{item['severity']}] {item['summary']}"
            )
    else:
        lines.append("- none")
    write_text(md_path, "\n".join(lines) + "\n")
    manifest["written_paths"] = {
        "json_path": str(json_path.relative_to(workspace)),
        "md_path": str(md_path.relative_to(workspace)),
    }
    write_json(json_path, manifest)
    return manifest


__all__ = ["build_contract_obligation_manifest", "emit_contract_obligation_manifest"]
