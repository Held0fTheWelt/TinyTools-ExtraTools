"""Ai policy for fy_platform.ai.policy.

"""
from __future__ import annotations

ADVISORY_ONLY_ACTIONS = {"prepare_fix", "triage", "compare", "explain", "prepare_context_pack"}
READ_ONLY_ACTIONS = {"inspect", "audit", "explain", "prepare_context_pack", "compare_runs"}
DECISION_LANES = {
    'safe_to_apply',
    'likely_but_review',
    'ambiguous',
    'user_input_required',
    'abstain',
}
SAFE_AUTO_LANES = {'safe_to_apply'}
REVIEW_REQUIRED_LANES = {'likely_but_review', 'ambiguous', 'user_input_required'}
ABSTAIN_LANES = {'abstain'}
