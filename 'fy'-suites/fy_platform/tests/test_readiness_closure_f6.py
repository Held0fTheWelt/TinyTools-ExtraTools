"""Tests for F6 review adjudication and closure decision hardening."""
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
            "summary": {"findings": 0, "files_with_findings": 0, "parse_errors": 0},
            "findings": [],
            "parse_errors": [],
        },
    )
    gen_root = ws / "documentify" / "generated" / "repo" / "documentify-run"
    _write(
        gen_root / "document_manifest.json",
        {
            "tracks": ["technical", "role-developer", "ai-read"],
            "generated_files": [
                "technical/SYSTEM_REFERENCE.md",
                "role-developer/README.md",
                "ai-read/bundle.md",
                "ai-read/bundle.json",
            ],
            "context": {"services": ["backend"]},
        },
    )
    _write(gen_root / "technical" / "SYSTEM_REFERENCE.md", "# system\n")
    _write(gen_root / "role-developer" / "README.md", "# role developer\n")
    _write(gen_root / "ai-read" / "bundle.md", "# ai bundle\n")
    _write(gen_root / "ai-read" / "bundle.json", {"ok": True})
    _write(
        ws / "mvpify" / "reports" / "mvpify_import_inventory.json",
        {"import_id": "import-1", "artifact_count": 3, "inventory": {"suite_signals": [{"name": "contractify", "present": True}, {"name": "testify", "present": True}, {"name": "despaghettify", "present": True}] }},
    )
    _write(ws / "mvpify" / "reports" / "mvpify_diagnosta_handoff.json", {"implementation_outcome": "implementation_ready_with_residue"})
    return ws


def test_f6_can_close_current_target_scope_while_keeping_warnings_visible(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    d = diagnosta.audit(str(ws))
    coda = CodaAdapter(root=ws)
    c = coda.audit(str(ws))

    assert d["readiness_case"]["readiness_status"] == "implementation_ready"
    assert d["warning_ledger"]["items"]
    assert d["residue_ledger"]["items"] == []

    pack = c["closure_pack"]
    review_packet = c["review_packet"]
    assert pack["status"] == "closed_for_current_target_reviewed_scope"
    assert pack["required_tests"] == []
    assert pack["required_docs"] == []
    assert pack["obligations"] == []
    assert len(pack["review_acceptances"]) == 8
    assert review_packet["status"] == "closed_for_current_target_reviewed_scope"
    assert review_packet["remaining_open_items"]["required_tests"] == []
    assert review_packet["remaining_open_items"]["required_docs"] == []
    assert review_packet["remaining_open_items"]["obligations"] == []


def test_f6_observifyfy_surfaces_review_packet_and_zero_open_burden(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    DiagnostaAdapter(root=ws).audit(str(ws))
    CodaAdapter(root=ws).audit(str(ws))
    payload = ObservifyfyAdapter(root=ws).audit(str(ws))

    assert payload["ok"] is True
    movement = payload["coda_signal"]["closure_movement"]
    assert payload["coda_signal"]["closure_pack"]["status"] == "closed_for_current_target_reviewed_scope"
    assert movement["obligation_count"] == 0
    assert movement["required_test_count"] == 0
    assert movement["required_doc_count"] == 0
    assert movement["accepted_review_item_count"] == 8
    assert movement["warning_count"] >= 3
