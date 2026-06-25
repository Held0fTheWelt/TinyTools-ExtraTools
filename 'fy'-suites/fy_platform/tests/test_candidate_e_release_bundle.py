"""Tests for Candidate E release bundle reporting."""
from __future__ import annotations

from fy_platform.ai.candidate_e_reporting import build_candidate_e_release_bundle
from fy_platform.ai.strategy_profiles import load_active_strategy_profile
from fy_platform.tests.test_candidate_e_profile import _mk_workspace


def test_candidate_e_release_bundle_restores_default_d_and_writes_comparison(tmp_path):
    ws = _mk_workspace(tmp_path)
    payload = build_candidate_e_release_bundle(ws)
    assert payload["comparison"]["material_difference_confirmed"] is True
    assert payload["manifest"]["default_profile"] == "D"
    assert load_active_strategy_profile(ws).active_profile == "D"
    assert (ws / payload["report_path"]).is_file()
    assert (ws / "docs" / "platform" / "self_hosting" / "candidate_e_d_vs_e_comparison.json").is_file()
    assert (ws / "docs" / "platform" / "examples" / "candidate_e" / "e" / "coda" / "latest_closure_pack.json").is_file()
