"""Final self-hosting and release-hardening tests for the Readiness-and-Closure MVP."""
from __future__ import annotations

import json
from pathlib import Path

from coda.adapter.service import CodaAdapter
from diagnosta.adapter.service import DiagnostaAdapter
from fy_platform.ai.final_product import (
    ai_capability_payload,
    command_reference_payload,
    render_ai_capability_markdown,
    render_command_reference_markdown,
    render_suite_catalog_markdown,
    suite_catalog_payload,
)
from fy_platform.ai.strategy_profiles import (
    load_active_strategy_profile,
    set_active_strategy_profile,
)
from fy_platform.ai.workspace import workspace_root, write_platform_doc_artifacts
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
                    "requires_human_review": True,
                }
            ],
            "manual_unresolved_areas": [],
            "actionable_units": ["Review the runtime envelope contract."],
        },
    )
    _write(
        ws / "testify" / "reports" / "testify_audit.json",
        {
            "summary": {"finding_count": 0, "warning_count": 1},
            "findings": [],
            "warnings": ["Weak workflow coverage for release gate."],
        },
    )
    _write(
        ws / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "proof_report.json",
        {"summary": {"finding_count": 0, "warning_count": 1}, "findings": [], "warnings": ["Weak workflow coverage for release gate."]},
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
        {"summary": {"finding_count": 0, "warning_count": 0, "required_service_count": 1, "present_service_count": 1}, "findings": [], "warnings": []},
    )
    _write(
        ws / "docify" / "baseline_docstring_coverage.json",
        {"summary": {"findings": 1, "files_with_findings": 1, "parse_errors": 0}, "findings": [{"path": "src/runtime.py", "line": 10, "kind": "function", "name": "run_turn", "code": "MISSING_OR_EMPTY_DOCSTRING"}], "parse_errors": []},
    )
    _write(
        ws / "documentify" / "generated" / "repo" / "documentify-run" / "document_manifest.json",
        {"tracks": ["technical", "role-developer"], "generated_files": ["technical/SYSTEM_REFERENCE.md", "role-developer/README.md"], "context": {"services": ["backend"]}},
    )
    _write(
        ws / "mvpify" / "reports" / "mvpify_import_inventory.json",
        {
            "import_id": "import-1",
            "artifact_count": 3,
            "inventory": {
                "suite_signals": [
                    {"name": "contractify", "present": True},
                    {"name": "testify", "present": True},
                    {"name": "despaghettify", "present": True},
                ]
            },
        },
    )
    _write(
        ws / "mvpify" / "reports" / "mvpify_orchestration_plan.json",
        {"highest_value_next_step": {"suite": "contractify", "objective": "Close contract drift."}},
    )
    return ws


def test_strategy_diagnosta_coda_end_to_end_and_profile_switching(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    assert load_active_strategy_profile(ws).active_profile == "D"
    set_active_strategy_profile(ws, "B")
    assert load_active_strategy_profile(ws).active_profile == "B"

    diagnosta = DiagnostaAdapter(root=ws)
    first = diagnosta.diagnose(str(ws))
    assert first["ok"] is True
    assert first["active_strategy_profile"]["active_profile"] == "B"

    set_active_strategy_profile(ws, "D")
    second = diagnosta.diagnose(str(ws))
    assert second["ok"] is True
    assert second["active_strategy_profile"]["active_profile"] == "D"

    delta = diagnosta.compare_runs(first["run_id"], second["run_id"])
    assert delta["ok"] is True
    assert delta["strategy_profile_changed"] is True

    coda = CodaAdapter(root=ws)
    closure = coda.closure_pack(str(ws))
    assert closure["ok"] is True
    assert closure["active_strategy_profile"]["active_profile"] == "D"
    assert closure["closure_pack"]["obligations"]
    assert closure["closure_pack"]["required_docs"] or closure["closure_pack"]["review_acceptances"]
    assert closure["closure_pack"]["affected_surfaces"]
    assert closure["review_packet"]["remaining_open_items"]["obligations"]
    assert closure["residue_ledger"]["items"]

    observify = ObservifyfyAdapter(root=ws)
    audit = observify.audit(str(ws))
    assert audit["ok"] is True
    assert audit["active_strategy_profile"]["active_profile"] == "D"
    assert audit["diagnosta_signal"]["present"] is True
    assert audit["coda_signal"]["present"] is True



def test_ai_capability_payload_includes_readiness_and_closure_suites(tmp_path: Path) -> None:
    payload = ai_capability_payload(tmp_path)
    assert "diagnosta" in payload["per_suite"]
    assert "coda" in payload["per_suite"]
    assert any("closure packs" in item for item in payload["per_suite"]["coda"])



def test_repo_self_hosting_release_artifacts_exist() -> None:
    workspace = workspace_root(Path(__file__))
    required = [
        workspace / "diagnosta" / "reports" / "latest_readiness_case.json",
        workspace / "coda" / "reports" / "latest_closure_pack.json",
        workspace / "observifyfy" / "reports" / "observifyfy_diagnosta_signal.json",
        workspace / "observifyfy" / "reports" / "observifyfy_coda_signal.json",
        workspace / "docs" / "platform" / "suite_catalog.json",
        workspace / "docs" / "platform" / "command_reference.json",
        workspace / "docs" / "platform" / "ai_capability_matrix.json",
        workspace / "docs" / "platform" / "READINESS_CLOSURE_FINAL_RELEASE_REPORT.md",
    ]
    for path in required:
        assert path.is_file(), f"missing expected release artifact: {path}"



def test_repo_release_docs_can_be_regenerated_from_current_workspace(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    catalog = suite_catalog_payload(ws)
    reference = command_reference_payload(ws)
    capability = ai_capability_payload(ws)
    write_platform_doc_artifacts(ws, stem="suite_catalog", json_payload=catalog, markdown_text=render_suite_catalog_markdown(catalog))
    write_platform_doc_artifacts(ws, stem="command_reference", json_payload=reference, markdown_text=render_command_reference_markdown(reference))
    write_platform_doc_artifacts(ws, stem="ai_capability_matrix", json_payload=capability, markdown_text=render_ai_capability_markdown(capability))
    assert (ws / "docs" / "platform" / "suite_catalog.json").is_file()
    assert (ws / "docs" / "platform" / "command_reference.json").is_file()
    assert (ws / "docs" / "platform" / "ai_capability_matrix.json").is_file()
