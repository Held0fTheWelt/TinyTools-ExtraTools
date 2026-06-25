"""Coda-facing export surfaces for Testify.

This module packages proof and test obligations from existing Testify outputs.
It stays bounded to current reports and generated proof artifacts.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, write_json, write_text

_REPORT_CANDIDATES = (
    Path("testify/reports/testify_audit.json"),
    Path("testify/reports/test_audit.json"),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _first_existing(workspace: Path) -> Path | None:
    for rel in _REPORT_CANDIDATES:
        path = workspace / rel
        if path.is_file():
            return path
    return None


def _latest_generated_match(workspace: Path, pattern: str) -> Path | None:
    matches = sorted(glob.glob(str(workspace / pattern)))
    if not matches:
        return None
    return Path(matches[-1])


def build_test_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Build a bounded Testify proof-obligation manifest for Coda."""
    report_path = _first_existing(workspace)
    proof_path = _latest_generated_match(
        workspace,
        "testify/generated/*/testify-*/evolution_graph/proof_report.json",
    )
    claim_path = _latest_generated_match(
        workspace,
        "testify/generated/*/testify-*/evolution_graph/claim_proof_status.json",
    )
    if report_path is None and proof_path is None:
        raise FileNotFoundError("No supported Testify report or proof artifact was found.")
    report = _load_json(report_path) if report_path else {}
    proof = _load_json(proof_path) if proof_path else {}
    claim = _load_json(claim_path) if claim_path else {}

    findings_source = report.get("findings") if report_path else None
    warnings_source = report.get("warnings") if report_path else None
    findings = list(findings_source if findings_source is not None else (proof.get("findings") or []))
    warnings = list(warnings_source if warnings_source is not None else (proof.get("warnings") or []))
    linked_claims = list(claim.get("linked_claims") or [])

    obligations: list[dict[str, Any]] = []
    required_tests: list[dict[str, Any]] = []
    highest_blocker_severity = 'low'

    for item in findings[:10]:
        obligation_id = str(item.get("id") or f"testify-finding-{len(obligations)+1}")
        summary = str(item.get("summary") or "Resolve a Testify proof finding.")
        severity = str(item.get("severity") or "medium")
        obligations.append(
            {
                "obligation_id": obligation_id,
                "suite": "testify",
                "category": "proof_finding",
                "severity": severity,
                "summary": summary,
                "review_required": True,
            }
        )
        required_tests.append(
            {
                "test_id": obligation_id,
                "suite": "testify",
                "severity": severity,
                "summary": summary,
                "source_kind": "proof_finding",
                "blocking": True,
            }
        )
        if severity == 'high' or (highest_blocker_severity != 'high' and severity == 'medium'):
            highest_blocker_severity = severity
    for index, item in enumerate(warnings[:8], start=1):
        required_tests.append(
            {
                "test_id": f"testify-warning-{index}",
                "suite": "testify",
                "severity": "medium",
                "summary": str(item),
                "source_kind": "warning",
                "blocking": False,
            }
        )
    for index, item in enumerate(linked_claims[:8], start=1):
        claim_id = str(item.get("claim_id") or f"linked-claim-{index}")
        required_tests.append(
            {
                "test_id": claim_id,
                "suite": "testify",
                "severity": "medium",
                "summary": f"Keep proof linkage healthy for claim `{claim_id}`.",
                "source_kind": "linked_claim",
                "workflow_path": item.get("workflow_path", ""),
                "blocking": False,
            }
        )

    manifest = {
        "schema_version": "fy.testify-coda-proof-obligation-manifest.v1",
        "suite": "testify",
        "generated_at": utc_now(),
        "source_report": str(report_path.relative_to(workspace)) if report_path else "",
        "proof_report_path": str(proof_path.relative_to(workspace)) if proof_path else "",
        "claim_proof_status_path": str(claim_path.relative_to(workspace)) if claim_path else "",
        "obligations": obligations,
        "required_tests": required_tests,
        "proof_family_status": {
            "blocker_gap_count": len(obligations),
            "warning_gap_count": len(warnings),
            "linked_claim_count": len(linked_claims),
            "highest_blocker_severity": highest_blocker_severity,
            "summary": (
                f"Testify sees {len(obligations)} blocker-class proof family gap(s), "
                f"{len(warnings)} warning-shaped proof item(s), and {len(linked_claims)} linked claim(s)."
            ),
        },
        "summary": (
            f"Testify exported {len(required_tests)} bounded required test/proof items "
            f"for closure-pack review."
        ),
    }
    return manifest


def emit_test_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Write the latest Testify proof/test obligation manifest for Coda."""
    manifest = build_test_obligation_manifest(workspace)
    reports = workspace / "testify" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest_coda_test_obligation_manifest.json"
    md_path = reports / "latest_coda_test_obligation_manifest.md"
    write_json(json_path, manifest)
    lines = [
        "# Testify Coda Proof/Test Obligation Manifest",
        "",
        manifest["summary"],
        "",
        f"- required_test_count: `{len(manifest['required_tests'])}`",
        f"- obligation_count: `{len(manifest['obligations'])}`",
        "",
    ]
    for item in manifest["required_tests"][:20]:
        lines.append(f"- `{item['test_id']}` [{item['severity']}] {item['summary']}")
    write_text(md_path, "\n".join(lines) + "\n")
    manifest["written_paths"] = {
        "json_path": str(json_path.relative_to(workspace)),
        "md_path": str(md_path.relative_to(workspace)),
    }
    write_json(json_path, manifest)
    return manifest


__all__ = ["build_test_obligation_manifest", "emit_test_obligation_manifest"]
