"""Derived execution-lane metadata for strategy profiles."""
from __future__ import annotations

from typing import Any


def behavior_for_profile(active_profile: str, *, allow_candidate_e_features: bool = False, candidate_e_requires_explicit_opt_in: bool = True) -> dict[str, Any]:
    """Return derived execution-lane metadata for the active profile."""
    normalized = str(active_profile or 'D').strip().upper() or 'D'
    if normalized == 'E' and allow_candidate_e_features:
        return {
            'profile_execution_lane': 'candidate_e_narrow_deep',
            'profile_behavior_depth': 'narrow_deep',
            'candidate_e_active': True,
            'candidate_e_opt_in_state': 'explicit_opt_in_active',
            'candidate_e_requires_explicit_opt_in': candidate_e_requires_explicit_opt_in,
            'orchestration_depth': 'deep',
            'planning_horizon': 3,
            'blocker_grouping_depth': 'dependency_clustered',
            'guarantee_gap_grouping': 'clustered',
            'handoff_depth': 'deep_structured',
            'closure_packet_depth': 'multi_wave_review_packets',
            'review_packet_depth': 'deep_review_packets',
            'bounded_auto_preparation': 'review_packet_only',
            'compare_profile_effects': 'required',
            'profile_comparison_hint': 'Candidate E deepens Diagnosta synthesis, handoff structure, Coda packetization, and wave planning.',
            'expected_distinction_from_d': [
                'deeper_blocker_grouping',
                'guarantee_gap_clustering',
                'multi_wave_planning',
                'richer_review_packets',
                'deeper_closure_packetization',
            ],
        }
    return {
        'profile_execution_lane': 'balanced_review_first',
        'profile_behavior_depth': 'standard',
        'candidate_e_active': False,
        'candidate_e_opt_in_state': 'inactive',
        'candidate_e_requires_explicit_opt_in': candidate_e_requires_explicit_opt_in,
        'orchestration_depth': 'standard',
        'planning_horizon': 1,
        'blocker_grouping_depth': 'standard',
        'guarantee_gap_grouping': 'standard',
        'handoff_depth': 'standard',
        'closure_packet_depth': 'standard',
        'review_packet_depth': 'standard',
        'bounded_auto_preparation': 'disabled',
        'compare_profile_effects': 'optional',
        'profile_comparison_hint': 'Candidate D is the stable balanced baseline for readiness and closure work.',
        'expected_distinction_from_d': [],
    }


__all__ = ['behavior_for_profile']
