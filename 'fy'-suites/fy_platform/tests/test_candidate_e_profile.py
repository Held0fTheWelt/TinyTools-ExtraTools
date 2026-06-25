"""Tests for Candidate E narrow-but-deep profile behavior."""
from __future__ import annotations

import json
from pathlib import Path

from coda.adapter.service import CodaAdapter
from diagnosta.adapter.service import DiagnostaAdapter
from fy_platform.ai.strategy_profiles import load_active_strategy_profile, set_active_strategy_profile, strategy_runtime_metadata
from fy_platform.tools.cli import main
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
        {"ast": {"global_category": "low", "local_spike_count": 0, "top12_longest": []}},
    )
    _write(
        ws / "dockerify" / "reports" / "dockerify_audit.json",
        {"summary": {"finding_count": 0, "warning_count": 1}, "findings": [], "warnings": ["missing health wait"]},
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


def test_candidate_e_requires_explicit_selection_and_emits_deeper_metadata(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    default_profile = load_active_strategy_profile(ws)
    assert default_profile.active_profile == "D"
    default_meta = strategy_runtime_metadata(ws)
    assert default_meta["candidate_e_active"] is False
    assert default_meta["planning_horizon"] == 1

    set_active_strategy_profile(ws, "E")
    profile = load_active_strategy_profile(ws)
    meta = strategy_runtime_metadata(ws)
    assert profile.active_profile == "E"
    assert profile.allow_candidate_e_features is True
    assert meta["candidate_e_active"] is True
    assert meta["candidate_e_opt_in_state"] == "explicit_opt_in_active"
    assert meta["planning_horizon"] == 3
    assert meta["handoff_depth"] == "deep_structured"


def test_candidate_e_can_be_selected_via_cli(tmp_path: Path, capsys) -> None:
    ws = _mk_workspace(tmp_path)
    code = main(["strategy", "set", "E", "--project-root", str(ws)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["active_profile"] == "E"
    meta = strategy_runtime_metadata(ws)
    assert meta["candidate_e_active"] is True
    assert meta["profile_execution_lane"] == "candidate_e_narrow_deep"


def test_candidate_e_diagnosta_and_coda_are_deeper_than_d(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    coda = CodaAdapter(root=ws)

    d_diag = diagnosta.audit(str(ws))
    d_coda = coda.audit(str(ws))

    set_active_strategy_profile(ws, "E")
    e_diag = diagnosta.audit(str(ws))
    e_coda = coda.audit(str(ws))

    assert d_diag["readiness_case"]["active_profile"] == "D"
    assert e_diag["readiness_case"]["active_profile"] == "E"
    assert d_diag["handoff_packet"]["depth"] == "standard"
    assert e_diag["handoff_packet"]["depth"] == "deep_structured"
    assert len(e_diag["deep_synthesis"]["guarantee_gap_clusters"]) > len(d_diag["deep_synthesis"]["guarantee_gap_clusters"])
    assert len(e_diag["deep_synthesis"]["next_wave_plan"]) > len(d_diag["deep_synthesis"]["next_wave_plan"])

    assert d_coda["closure_pack"]["packet_depth"] == "standard"
    assert e_coda["closure_pack"]["packet_depth"] == "multi_wave_review_packets"
    assert len(e_coda["closure_pack"]["wave_packets"]) > len(d_coda["closure_pack"]["wave_packets"])
    assert len(e_coda["closure_pack"]["auto_preparation_packets"]) > len(d_coda["closure_pack"]["auto_preparation_packets"])
    assert len(e_coda["review_packet"]["sections"]) > len(d_coda["review_packet"]["sections"])


def test_candidate_e_profile_difference_is_visible_in_compare_runs_and_observifyfy(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    coda = CodaAdapter(root=ws)

    d_run = diagnosta.audit(str(ws))
    d_coda = coda.audit(str(ws))
    set_active_strategy_profile(ws, "E")
    e_run = diagnosta.audit(str(ws))
    e_coda = coda.audit(str(ws))

    diag_delta = diagnosta.compare_runs(d_run["run_id"], e_run["run_id"])
    coda_delta = coda.compare_runs(d_coda["run_id"], e_coda["run_id"])
    obs = ObservifyfyAdapter(root=ws).audit(str(ws))

    assert diag_delta["profile_depth_delta"]["active_profile_changed"] is True
    assert diag_delta["profile_depth_delta"]["planning_horizon_delta"] == 2
    assert diag_delta["handoff_depth_delta"]["depth_changed"] is True
    assert coda_delta["closure_pack_delta"]["wave_packet_delta_count"] > 0
    assert coda_delta["closure_pack_delta"]["packet_depth_changed"] is True
    assert obs["diagnosta_signal"]["profile_depth_signal"]["profile_behavior_depth"] == "narrow_deep"
    assert obs["coda_signal"]["closure_movement"]["packet_depth"] == "multi_wave_review_packets"
    assert obs["coda_signal"]["closure_movement"]["wave_packet_count"] > 0
