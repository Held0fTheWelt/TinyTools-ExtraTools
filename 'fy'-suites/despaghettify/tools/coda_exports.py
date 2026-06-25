"""Coda-facing export surfaces for Despaghettify.

This module exports bounded insertion-surface and structural-risk data so
Coda can describe where work is likely to land and what structural hazards
should stay explicit in the closure pack.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, write_json, write_text


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_path(workspace: Path) -> Path | None:
    direct = workspace / "despaghettify" / "reports" / "latest_check_with_metrics.json"
    if direct.is_file():
        return direct
    latest_run = [Path(item) for item in glob.glob(str(workspace / ".fydata/runs/despaghettify/*/despag_audit.json"))]
    if latest_run:
        return max(latest_run, key=lambda item: (item.stat().st_mtime_ns, str(item)))
    matches = sorted(
        glob.glob(
            str(
                workspace
                / "despaghettify/generated/*/despaghettify-*/evolution_graph/structure_drift_report.json"
            )
        )
    )
    if matches:
        return Path(matches[-1])
    return None




def _is_repo_actionable_path(path: str) -> bool:
    return bool(path) and not path.startswith((
        'mvpify/imports/',
        'docs/MVPs/imports/',
        '.fydata/',
        'generated/',
        'examples/',
    ))




PACKETIZED_REVIEW_PREFIXES = (
    "docify/tools/",
    "testify/tools/",
    "mvpify/tools/",
    "contractify/tools/runtime_mvp_spine_",
    "documentify/tools/track_audience_",
    "documentify/tools/track_evidence_",
    "fy_platform/ai/final_product_schema_",
    "fy_platform/ai/evidence_registry/",
)

BLOCKER_CLASS_PREFIXES = (
    "fy_platform/ai/",
    "documentify/tools/",
    "contractify/tools/",
)


def _is_blocker_class_hotspot(risk: dict[str, Any]) -> bool:
    path = str(risk.get("source_path") or "")
    severity = str(risk.get("severity") or "")
    if severity not in {"high", "medium"}:
        return False
    if any(path.startswith(prefix) for prefix in PACKETIZED_REVIEW_PREFIXES):
        return False
    return any(path.startswith(prefix) for prefix in BLOCKER_CLASS_PREFIXES)


def _risk_from_summary(item: Any, default_severity: str = "medium") -> dict[str, Any]:
    if isinstance(item, dict):
        source_path = str(item.get("path") or item.get("file") or item.get("unit") or "")
        summary = str(item.get("summary") or item.get("name") or item)
        severity = str(item.get("severity") or default_severity)
    else:
        source_path = ""
        summary = str(item)
        severity = default_severity
    return {
        "risk_id": f"despaghettify-risk-{abs(hash((summary, source_path))) % 10_000_000}",
        "suite": "despaghettify",
        "severity": severity,
        "summary": summary,
        "source_path": source_path,
    }


def build_insertion_surface_report(workspace: Path) -> dict[str, Any]:
    """Build a bounded insertion-surface report for Coda."""
    path = _candidate_path(workspace)
    if path is None:
        raise FileNotFoundError("No supported Despaghettify structure report was found.")
    payload = _load_json(path)
    metrics_bundle = payload.get("metrics_bundle") or {}
    ast = metrics_bundle.get("ast") or payload.get("ast") or payload

    affected_surfaces: list[dict[str, Any]] = []
    structural_risks: list[dict[str, Any]] = []

    file_hotspots = list(payload.get("file_spikes") or metrics_bundle.get("file_spikes") or ast.get("file_spikes") or ast.get("top12_longest") or [])
    function_hotspots = list(payload.get("function_spikes") or metrics_bundle.get("function_spikes") or ast.get("function_spikes") or ast.get("top6_nesting") or [])

    for item in file_hotspots:
        if isinstance(item, dict):
            surface_path = str(item.get("path") or item.get("file") or item.get("module") or "")
            summary = str(item.get("summary") or item.get("name") or surface_path or "Long file hotspot")
        else:
            surface_path = str(item)
            summary = surface_path
        if not _is_repo_actionable_path(surface_path):
            continue
        affected_surfaces.append(
            {
                "surface_id": f"despag-surface-{abs(hash((surface_path, summary))) % 10_000_000}",
                "suite": "despaghettify",
                "path": surface_path,
                "summary": summary,
                "surface_kind": "file_hotspot",
            }
        )
        structural_risks.append(_risk_from_summary(item, default_severity="medium"))
    for item in function_hotspots:
        risk = _risk_from_summary(item, default_severity="high")
        if _is_repo_actionable_path(str(risk.get("source_path") or "")):
            structural_risks.append(risk)
    if ast.get("ai_turn_executor"):
        risk = _risk_from_summary(ast.get("ai_turn_executor"), default_severity="high")
        if _is_repo_actionable_path(str(risk.get("source_path") or "")):
            structural_risks.append(risk)
    for item in list(payload.get("ownership_hotspots") or []):
        risk = _risk_from_summary(item, default_severity=str(item.get("severity") or "medium"))
        if _is_repo_actionable_path(str(risk.get("source_path") or "")):
            structural_risks.append(risk)

    affected_surfaces = affected_surfaces[:8]
    structural_risks = structural_risks[:14]
    blocking_hotspots = [item for item in structural_risks if _is_blocker_class_hotspot(item)]

    report = {
        "schema_version": "fy.despaghettify-coda-insertion-surface-report.v1",
        "suite": "despaghettify",
        "generated_at": utc_now(),
        "source_report": str(path.relative_to(workspace)),
        "affected_surfaces": affected_surfaces,
        "structural_risks": structural_risks,
        "hotspot_decision_packet": {
            "blocking_hotspots": blocking_hotspots,
            "non_blocking_hotspots": [item for item in structural_risks if item not in blocking_hotspots],
            "highest_blocking_severity": (blocking_hotspots[0].get("severity") if blocking_hotspots else "low"),
            "summary": (
                f"Despaghettify sees {len(blocking_hotspots)} blocking hotspot(s) and "
                f"{len(structural_risks) - len(blocking_hotspots)} packetized non-blocking hotspot(s)."
            ),
        },
        "summary": (
            f"Despaghettify exported {len(affected_surfaces)} affected surface(s) and "
            f"{len(structural_risks)} bounded structural risk signal(s)."
        ),
    }
    return report


def emit_insertion_surface_report(workspace: Path) -> dict[str, Any]:
    """Write the latest Despaghettify insertion-surface report for Coda."""
    report = build_insertion_surface_report(workspace)
    reports = workspace / "despaghettify" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest_coda_insertion_surface_report.json"
    md_path = reports / "latest_coda_insertion_surface_report.md"
    write_json(json_path, report)
    lines = [
        "# Despaghettify Coda Insertion Surface Report",
        "",
        report["summary"],
        "",
        f"- affected_surface_count: `{len(report['affected_surfaces'])}`",
        f"- structural_risk_count: `{len(report['structural_risks'])}`",
        "",
    ]
    for item in report["affected_surfaces"][:20]:
        lines.append(f"- `{item['path']}` — {item['summary']}")
    write_text(md_path, "\n".join(lines) + "\n")
    report["written_paths"] = {
        "json_path": str(json_path.relative_to(workspace)),
        "md_path": str(md_path.relative_to(workspace)),
    }
    write_json(json_path, report)
    return report


__all__ = ["build_insertion_surface_report", "emit_insertion_surface_report"]
