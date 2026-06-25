"""Tests for F5 residue tightening and closure reclassification."""
from __future__ import annotations

import json
from pathlib import Path

from coda.adapter.service import CodaAdapter
from diagnosta.adapter.service import DiagnostaAdapter
from observifyfy.adapter.service import ObservifyfyAdapter


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _mk_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    _write(ws / "README.md", "# Workspace\n")
    _write(ws / "pyproject.toml", "[project]\nname=\"workspace\"\nversion=\"0.1.0\"\n")
    _write(ws / "fy_governance_enforcement.yaml", "ok: true\n")
    for req in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
        _write(ws / req, "pytest\n")
    _write(ws / "FY_STRATEGY_SETTINGS.md", "# FY Strategy Settings\n\n- active_profile: D\n")

    for suite in [
        "contractify",
        "testify",
        "despaghettify",
        "dockerify",
        "docify",
        "documentify",
        "mvpify",
        "diagnosta",
        "coda",
        "observifyfy",
    ]:
        for rel in ["adapter", "tools", "reports/status", "state", "templates"]:
            (ws / suite / rel).mkdir(parents=True, exist_ok=True)
        _write(ws / suite / "README.md", f"# {suite}\n")
        _write(ws / suite / "adapter" / "service.py", "class X: pass\n")
        _write(ws / suite / "adapter" / "cli.py", "def main():\n    return 0\n")

    runtime = ws / "src" / "runtime.py"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text("def run_turn():\n    return True\n", encoding="utf-8")

    _write(
        ws / "contractify" / "reports" / "audit_latest.json",
        {"drift_findings": [], "conflicts": [], "manual_unresolved_areas": [], "actionable_units": []},
    )
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {"summary": {"finding_count": 0, "warning_count": 1}, "findings": [], "warnings": ["workflow coverage is bundled elsewhere"]},
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "proof_report.json",
        {"summary": {"finding_count": 0, "warning_count": 1}, "findings": [], "warnings": ["workflow coverage is bundled elsewhere"]},
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "claim_proof_status.json",
        {"family_gap_count": 0, "linked_claim_count": 1, "linked_claims": [{"claim_id": "claim-runtime", "workflow_path": ".github/workflows/ci.yml"}]},
    )
    _write(
        ws / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {"ast": {"global_category": "low", "local_spike_count": 1, "top12_longest": [{"path": "src/runtime.py", "summary": "Large runtime file hotspot."}] }},
    )
    _write(
        ws / "dockerify" / "reports" / "dockerify_audit.json",
        {"summary": {"finding_count": 0, "warning_count": 2}, "findings": [], "warnings": ["missing health wait", "missing env file"]},
    )
    _write(
        ws / "docify" / "baseline_docstring_coverage.json",
        {
            "summary": {"findings": 2, "files_with_findings": 1, "parse_errors": 1},
            "findings": [
                {"path": "src/runtime.py", "line": 10, "kind": "function", "name": "run_turn", "code": "MISSING_OR_EMPTY_DOCSTRING"},
                {"path": "missing/ghost.py", "line": 1, "kind": "function", "name": "ghost", "code": "MISSING_OR_EMPTY_DOCSTRING"},
            ],
            "parse_errors": ["src/runtime.py: SyntaxError: boom", "missing/ghost.py: SyntaxError: boom"],
        },
    )
    _write(
        ws / "documentify" / "generated" / "repo" / "documentify-run" / "document_manifest.json",
        {
            "tracks": ["technical", "role-developer", "status", "ai-read"],
            "generated_files": [
                "technical/SYSTEM_REFERENCE.md",
                "role-developer/README.md",
                "ai-read/bundle.md",
                "ai-read/bundle.json",
                "status/MOST_RECENT_NEXT_STEPS.md",
            ],
            "context": {"services": ["backend"]},
        },
    )
    _write(
        ws / "mvpify" / "reports" / "mvpify_import_inventory.json",
        {"import_id": "import-1", "artifact_count": 3, "inventory": {"suite_signals": [{"name": "contractify", "present": True}, {"name": "testify", "present": True}, {"name": "despaghettify", "present": True}] }},
    )
    _write(ws / "mvpify" / "reports" / "mvpify_diagnosta_handoff.json", {"implementation_outcome": "implementation_ready_with_residue"})
    return ws


def test_f5_reclassifies_non_blocking_signals_as_warnings_and_tightens_required_docs(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    d = diagnosta.audit(str(ws))
    coda = CodaAdapter(root=ws)
    c = coda.audit(str(ws))

    readiness = d["readiness_case"]
    d_residue = d["residue_ledger"]
    d_warning = d["warning_ledger"]
    pack = c["closure_pack"]
    c_residue = c["residue_ledger"]
    c_warning = c["warning_ledger"]

    assert readiness["readiness_status"] == "implementation_ready"
    assert readiness["blocker_ids"] == []
    assert "warning:testify:proof-items" in readiness["warning_ids"]
    assert "warning:dockerify:warnings" in readiness["warning_ids"]
    assert "warning:readiness:optional-evidence-missing" in readiness["warning_ids"]
    assert d_residue["items"] == []
    assert len(d_warning["items"]) >= 3

    assert pack["status"] == "bounded_review_ready"
    assert c_residue["items"] == []
    assert len(c_warning["items"]) >= 3
    assert len(pack["required_docs"]) == 4
    assert all(not item["path"].endswith(".json") for item in pack["required_docs"])
    assert all(not item["path"].startswith("status/") for item in pack["required_docs"])


def test_f5_observifyfy_surfaces_warning_counts_and_stronger_bounded_status(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    DiagnostaAdapter(root=ws).audit(str(ws))
    CodaAdapter(root=ws).audit(str(ws))
    payload = ObservifyfyAdapter(root=ws).audit(str(ws))
    assert payload["ok"] is True
    assert payload["diagnosta_signal"]["readiness_case"]["readiness_status"] == "implementation_ready"
    assert payload["coda_signal"]["closure_pack"]["status"] == "bounded_review_ready"
    assert payload["coda_signal"]["closure_movement"]["warning_count"] >= 3
    assert payload["coda_signal"]["closure_movement"]["residue_count"] == 0
