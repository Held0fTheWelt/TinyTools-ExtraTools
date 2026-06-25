"""Tests for readiness-and-closure wave 4 cross-suite closure wiring."""
from __future__ import annotations

import json
from pathlib import Path

from coda.adapter.service import CodaAdapter
from observifyfy.adapter.service import ObservifyfyAdapter


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def _mk_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    _write(ws / "README.md", "# Workspace\n")
    _write(ws / "pyproject.toml", "[project]\nname=\"workspace\"\nversion=\"0.1.0\"\n")
    _write(ws / "fy_governance_enforcement.yaml", "ok: true\n")
    _write(ws / "requirements.txt", "pytest\n")
    _write(ws / "requirements-dev.txt", "pytest\n")
    _write(ws / "requirements-test.txt", "pytest\n")
    _write(
        ws / "FY_STRATEGY_SETTINGS.md",
        "# FY Strategy Settings\n\n"
        "- active_profile: D\n"
        "- default_progression_order: A,B,C,D,E\n"
        "- progression_mode: progressive\n"
        "- allow_profile_switching: true\n"
        "- command_enabled: true\n"
        "- emit_profile_to_run_journal: true\n"
        "- emit_profile_to_observifyfy: true\n"
        "- emit_profile_to_compare_runs: true\n",
    )

    for suite in [
        "contractify",
        "testify",
        "despaghettify",
        "docify",
        "documentify",
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
        {
            "drift_findings": [
                {
                    "id": "CTR-DRIFT-1",
                    "severity": "high",
                    "summary": "Contract drift around runtime envelope.",
                    "evidence_sources": ["docs/ADR/adr-1.md", "src/runtime.py"],
                }
            ],
            "conflicts": [
                {
                    "id": "CTR-CNF-1",
                    "severity": "medium",
                    "summary": "Normative wording overlap requires review.",
                    "sources": ["docs/ADR/adr-2.md"],
                }
            ],
            "manual_unresolved_areas": [],
            "actionable_units": ["Review the runtime envelope contract."],
        },
    )
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {
            "findings": [
                {
                    "id": "TEST-1",
                    "severity": "high",
                    "summary": "Missing runtime contract regression test.",
                }
            ],
            "warnings": ["Weak workflow coverage for release gate."],
        },
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "proof_report.json",
        {
            "findings": [
                {
                    "id": "TEST-1",
                    "severity": "high",
                    "summary": "Missing runtime contract regression test.",
                }
            ],
            "warnings": ["Weak workflow coverage for release gate."],
        },
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "claim_proof_status.json",
        {"linked_claims": [{"claim_id": "claim-runtime", "workflow_path": ".github/workflows/ci.yml"}]},
    )
    _write(
        ws / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {
            "ast": {
                "top12_longest": [
                    {"path": "src/runtime.py", "summary": "Large runtime file hotspot."}
                ],
                "top6_nesting": [
                    {"path": "src/runtime.py", "summary": "High nesting in runtime coordinator."}
                ],
                "ai_turn_executor": {
                    "path": "src/runtime.py",
                    "summary": "AI turn executor remains structurally risky.",
                },
            }
        },
    )
    _write(
        ws / "docify" / "baseline_docstring_coverage.json",
        {
            "summary": {"findings": 1, "files_with_findings": 1, "parse_errors": 0},
            "findings": [
                {
                    "path": "src/runtime.py",
                    "line": 10,
                    "kind": "function",
                    "name": "run_turn",
                    "code": "MISSING_OR_EMPTY_DOCSTRING",
                }
            ],
            "parse_errors": [],
        },
    )
    _write(
        ws / "documentify" / "generated" / "repo" / "documentify-run" / "document_manifest.json",
        {
            "tracks": ["technical", "role-developer"],
            "generated_files": [
                "technical/SYSTEM_REFERENCE.md",
                "role-developer/README.md",
            ],
            "context": {"services": ["backend"]},
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_readiness_case.json",
        {
            "schema_version": "fy.readiness-case.v1",
            "target_id": "workspace:workspace",
            "readiness_status": "implementation_ready",
            "summary": "Readiness is bounded but good enough for review-first closure assembly.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_blocker_graph.json",
        {
            "schema_version": "fy.blocker-graph.v1",
            "nodes": [],
            "edges": [],
            "summary": "No remaining blockers in this bounded fixture.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_blocker_priority_report.json",
        {
            "schema_version": "fy.blocker-priority-report.v1",
            "priorities": [],
            "blocker_count": 0,
            "summary": "No prioritized blockers remain.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_obligation_matrix.json",
        {
            "schema_version": "fy.obligation-matrix.v1",
            "rows": [
                {
                    "obligation_id": "diag-1",
                    "suite": "diagnosta",
                    "category": "readiness_review",
                    "severity": "medium",
                    "summary": "Keep review of the readiness case explicit.",
                    "source_paths": ["diagnosta/reports/latest_readiness_case.json"],
                }
            ],
            "summary": "One bounded readiness obligation remains reviewable.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_cannot_honestly_claim.json",
        {
            "schema_version": "fy.cannot-honestly-claim.v1",
            "blocked_claims": [],
            "summary": "No extra blocked claims in this bounded fixture.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_residue_ledger.json",
        {
            "schema_version": "fy.residue-ledger.v1",
            "items": [],
            "summary": "No inherited residue in this bounded fixture.",
        },
    )
    _write(
        ws / "diagnosta" / "reports" / "latest_sufficiency_verdict.json",
        {
            "schema_version": "fy.sufficiency-verdict.v1",
            "verdict": "bounded_sufficient",
            "summary": "Supporting evidence is bounded-sufficient for review-first closure assembly.",
        },
    )
    return ws


def test_coda_closure_pack_includes_tests_docs_obligations_and_surfaces(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    adapter = CodaAdapter(root=ws)
    result = adapter.closure_pack(str(ws))
    assert result["ok"] is True
    pack = result["closure_pack"]
    assert pack["obligations"]
    assert any(item["suite"] == "contractify" for item in pack["obligations"])
    assert pack["required_tests"]
    assert any(item["suite"] == "testify" for item in pack["required_tests"])
    assert pack["required_docs"]
    assert any(item["suite"] == "docify" for item in pack["obligations"])
    assert any(item["suite"] == "documentify" for item in pack["required_docs"])
    assert pack["affected_surfaces"]
    assert any(item["suite"] == "despaghettify" for item in pack["affected_surfaces"])
    assert (ws / "contractify" / "reports" / "latest_coda_obligation_manifest.json").is_file()
    assert (ws / "testify" / "reports" / "latest_coda_test_obligation_manifest.json").is_file()
    assert (ws / "docify" / "reports" / "latest_coda_documentation_manifest.json").is_file()
    assert (ws / "documentify" / "reports" / "latest_coda_documentation_manifest.json").is_file()


def test_missing_supporting_evidence_yields_residue_not_false_closure(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    (ws / "docify" / "baseline_docstring_coverage.json").unlink()
    (ws / "documentify" / "generated").rename(ws / "documentify" / "generated_missing")
    adapter = CodaAdapter(root=ws)
    result = adapter.closure_pack(str(ws))
    assert result["ok"] is True
    pack = result["closure_pack"]
    residue = result["residue_ledger"]
    assert pack["status"] == "bounded_partial_closure"
    residue_ids = {item["residue_id"] for item in residue["items"]}
    assert "residue:coda:missing-supporting-export:docify" in residue_ids
    assert "residue:coda:missing-supporting-export:documentify" in residue_ids


def test_coda_compare_runs_reports_meaningful_closure_pack_deltas(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    adapter = CodaAdapter(root=ws)
    first = adapter.closure_pack(str(ws))
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {
            "findings": [
                {
                    "id": "TEST-1",
                    "severity": "high",
                    "summary": "Missing runtime contract regression test.",
                },
                {"id": "TEST-2", "severity": "medium", "summary": "Add release smoke test."},
            ],
            "warnings": ["Weak workflow coverage for release gate."],
        },
    )
    second = adapter.closure_pack(str(ws))
    delta = adapter.compare_runs(first["run_id"], second["run_id"])
    assert delta["ok"] is True
    assert delta["closure_pack_delta"]["required_test_delta_count"] > 0


def test_observifyfy_surfaces_closure_pack_movement_and_profile(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    coda = CodaAdapter(root=ws)
    coda.closure_pack(str(ws))
    adapter = ObservifyfyAdapter(root=ws)
    result = adapter.audit(str(ws))
    assert result["ok"] is True
    assert result["active_strategy_profile"]["active_profile"] == "D"
    coda_signal = result["coda_signal"]
    assert coda_signal["present"] is True
    assert coda_signal["closure_movement"]["obligation_count"] > 0
    assert result["next_steps"]["recommended_next_steps"]
