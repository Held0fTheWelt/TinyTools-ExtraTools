"""F2 follow-on tests for proof-family and hotspot handling."""
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
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _mk_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    _write(ws / "README.md", "# Workspace\n")
    _write(ws / "pyproject.toml", "[project]\nname='workspace'\nversion='0.1.0'\n")
    _write(ws / "fy_governance_enforcement.yaml", "ok: true\n")
    for name in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
        _write(ws / name, "pytest\n")
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
        _write(ws / suite / "adapter" / "service.py", "class Placeholder: pass\n")
        _write(ws / suite / "adapter" / "cli.py", "def main():\n    return 0\n")
    _write(
        ws / "contractify" / "reports" / "audit_latest.json",
        {
            "drift_findings": [],
            "conflicts": [],
            "manual_unresolved_areas": [],
            "actionable_units": [],
        },
    )
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {
            "summary": {"finding_count": 0, "warning_count": 1},
            "findings": [],
            "warnings": ["frontend workflow is bundled elsewhere"],
        },
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "claim_proof_status.json",
        {"linked_claims": [{"claim_id": "claim-1", "workflow_path": ".github/workflows/ci.yml"}]},
    )
    _write(
        ws / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {
            "file_spikes": [
                {
                    "path": "documentify/tools/track_engine.py",
                    "line_count": 704,
                    "severity": "high",
                },
                {
                    "path": "mvpify/imports/x/normalized/source_tree/diagnosta/tools/analysis.py",
                    "line_count": 700,
                    "severity": "high",
                },
            ],
            "function_spikes": [
                {
                    "path": "documentify/tools/track_engine.py",
                    "name": "render_track",
                    "line_span": 120,
                    "severity": "medium",
                }
            ],
        },
    )
    _write(
        ws / "docify" / "baseline_docstring_coverage.json",
        {
            "summary": {"findings": 1, "files_with_findings": 1, "parse_errors": 0},
            "findings": [
                {
                    "path": "documentify/tools/track_engine.py",
                    "name": "render_track",
                    "code": "MISSING",
                }
            ],
            "parse_errors": [],
        },
    )
    _write(
        ws / "documentify" / "generated" / "repo" / "documentify-run" / "document_manifest.json",
        {
            "tracks": ["technical"],
            "generated_files": ["technical/SYSTEM_REFERENCE.md"],
            "context": {},
        },
    )
    return ws


def test_diagnosta_drops_testify_blocker_when_only_warnings_and_linked_claims_remain(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    result = DiagnostaAdapter(root=ws).diagnose(str(ws))
    blocker_ids = {item["blocker_id"] for item in result["blocker_priority_report"]["priorities"]}
    assert "blocker:testify:proof-family-gaps" not in blocker_ids
    assert "blocker:despaghettify:local-hotspots" in blocker_ids
    assert any(item["warning_id"] == "warning:testify:proof-items" for item in result["warning_ledger"]["items"])


def test_coda_compare_runs_tracks_required_test_delta_from_refreshed_testify_inputs(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    diagnosta.diagnose(str(ws))
    coda = CodaAdapter(root=ws)
    first = coda.closure_pack(str(ws))
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {
            "summary": {"finding_count": 1, "warning_count": 1},
            "findings": [
                {
                    "id": "TEST-1",
                    "severity": "high",
                    "summary": "Add runtime regression test.",
                }
            ],
            "warnings": ["frontend workflow is bundled elsewhere"],
        },
    )
    diagnosta.diagnose(str(ws))
    second = coda.closure_pack(str(ws))
    delta = coda.compare_runs(first["run_id"], second["run_id"])
    assert delta["ok"] is True
    assert delta["closure_pack_delta"]["required_test_delta_count"] > 0


def test_observifyfy_surfaces_refreshed_readiness_and_closure_after_f2(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    DiagnostaAdapter(root=ws).diagnose(str(ws))
    CodaAdapter(root=ws).closure_pack(str(ws))
    audit = ObservifyfyAdapter(root=ws).audit(str(ws))
    assert audit["ok"] is True
    assert audit["diagnosta_signal"]["present"] is True
    assert audit["coda_signal"]["present"] is True
