"""Tests for F7 terminal label freeze and final reporting."""
from __future__ import annotations

from pathlib import Path

from coda.adapter.service import CodaAdapter
from diagnosta.adapter.service import DiagnostaAdapter
from fy_platform.ai.readiness_closure_final_reporting import write_final_release_bundle
from observifyfy.adapter.service import ObservifyfyAdapter
from fy_platform.tests.test_readiness_closure_f6 import _mk_workspace


def test_f7_freezes_terminal_label_when_reviewed_scope_state_remains_stable(tmp_path: Path) -> None:
    ws = _mk_workspace(tmp_path)
    DiagnostaAdapter(root=ws).audit(str(ws))
    CodaAdapter(root=ws).audit(str(ws))
    ObservifyfyAdapter(root=ws).audit(str(ws))

    bundle = write_final_release_bundle(ws)

    manifest = bundle["terminal_manifest"]
    assert manifest["terminal_label"] == "closed_for_current_target_reviewed_scope"
    assert manifest["terminal_label_frozen"] is True
    assert manifest["blocker_count"] == 0
    assert manifest["residue_count"] == 0
    assert manifest["open_obligation_count"] == 0
    assert manifest["open_required_test_count"] == 0
    assert manifest["open_required_doc_count"] == 0
    assert manifest["warning_count"] == 4

    decision = (ws / "docs/platform/FINAL_CURRENT_TARGET_CLOSURE_DECISION.md").read_text(encoding="utf-8")
    boundary = (ws / "docs/platform/FINAL_CURRENT_TARGET_CLAIM_BOUNDARY.md").read_text(encoding="utf-8")
    terminal = (ws / "docs/platform/self_hosting/readiness_closure_final_terminal_manifest.json").read_text(encoding="utf-8")
    summary = (ws / "observifyfy/reports/observifyfy_final_readiness_closure_summary.json").read_text(encoding="utf-8")

    assert "closed_for_current_target_reviewed_scope" in decision
    assert "What is still not claimable" in boundary
    assert "terminal_label_frozen" in terminal
    assert "closed_for_current_target_reviewed_scope" in summary
