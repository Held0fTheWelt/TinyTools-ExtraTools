"""Regression guard for the canonical Candidate E closure report."""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.strategy_profiles import load_active_strategy_profile


def test_candidate_e_closure_report_is_canonical_and_backed_by_real_repo_evidence() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    md_report = repo_root / 'docs' / 'platform' / 'READINESS_CLOSURE_CANDIDATE_E_CLOSURE_REPORT.md'
    json_report = repo_root / 'docs' / 'platform' / 'READINESS_CLOSURE_CANDIDATE_E_CLOSURE_REPORT.json'

    assert md_report.is_file()
    assert json_report.is_file()

    payload = json.loads(json_report.read_text(encoding='utf-8'))

    assert payload['default_profile'] == 'D'
    assert payload['candidate_e_opt_in'] is True
    assert payload['material_difference_confirmed'] is True
    assert payload['diagnosta_deeper_under_e'] is True
    assert payload['handoff_deeper_under_e'] is True
    assert payload['coda_deeper_under_e'] is True
    assert payload['review_first_preserved'] is True
    assert payload['warnings_visible'] is True
    assert payload['cannot_honestly_claim_preserved'] is True
    assert payload['silent_auto_apply_detected'] is False
    assert payload['fake_autonomous_closure_detected'] is False
    assert payload['restored_profile_after_proof'] == 'D'

    proof_sources = payload['proof_sources']
    assert isinstance(proof_sources, list) and proof_sources
    for rel_path in proof_sources:
        assert (repo_root / rel_path).is_file(), rel_path

    active_strategy_file = repo_root / 'fy_platform' / 'state' / 'strategy_profiles' / 'FY_ACTIVE_STRATEGY.md'
    if active_strategy_file.is_file():
        profile = load_active_strategy_profile(repo_root)
        assert profile.active_profile == 'D'
        assert profile.allow_candidate_e_features is False
