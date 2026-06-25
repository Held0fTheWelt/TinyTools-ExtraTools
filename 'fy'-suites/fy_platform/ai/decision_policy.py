"""Decision policy for fy_platform.ai.

"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DECISION_LANES = {
    'safe_to_apply': 'The evidence is strong enough for a safe automatic action.',
    'likely_but_review': 'There is a likely good solution, but a human should review it first.',
    'ambiguous': 'There are multiple plausible solutions, so the system should not choose silently.',
    'user_input_required': 'A required mapping or instruction is missing, so the user must decide.',
    'abstain': 'The evidence is too weak or too risky for automatic action.',
}


@dataclass(frozen=True)
class DecisionAssessment:
    """Coordinate decision assessment behavior.
    """
    lane: str
    confidence: str
    can_auto_apply: bool
    reason: str
    evidence_strength: str
    uncertainty_flags: list[str] = field(default_factory=list)
    recommended_action: str = ''


def _confidence_bucket(score: float) -> str:
    """Confidence bucket.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        score: Primary score used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    # Branch on score >= 0.9 so _confidence_bucket only continues along the matching
    # state path.
    if score >= 0.9:
        return 'high'
    # Branch on score >= 0.7 so _confidence_bucket only continues along the matching
    # state path.
    if score >= 0.7:
        return 'medium'
    return 'low'


def assess_solution_decision(
    *,
    explicit_instruction: bool,
    candidate_count: int,
    top_score: float,
    second_score: float = 0.0,
    high_risk: bool = False,
    requires_complete_mapping: bool = False,
    missing_required_mapping: bool = False,
) -> DecisionAssessment:
    """Assess solution decision.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        explicit_instruction: Whether to enable this optional behavior.
        candidate_count: Primary candidate count used by this step.
        top_score: Primary top score used by this step.
        second_score: Primary second score used by this step.
        high_risk: Whether to enable this optional behavior.
        requires_complete_mapping: Whether to enable this optional
            behavior.
        missing_required_mapping: Whether to enable this optional
            behavior.

    Returns:
        DecisionAssessment:
            Value produced by this callable as
            ``DecisionAssessment``.
    """
    uncertainty: list[str] = []
    gap = top_score - second_score
    confidence = _confidence_bucket(top_score)

    if missing_required_mapping:
        return DecisionAssessment(
            lane='user_input_required',
            confidence='low',
            can_auto_apply=False,
            reason='required_mapping_missing',
            evidence_strength='insufficient',
            uncertainty_flags=['missing_required_mapping'],
            recommended_action='Ask for explicit user instruction or mapping before changing outward files.',
        )

    if candidate_count <= 0 or top_score <= 0:
        return DecisionAssessment(
            lane='abstain',
            confidence='low',
            can_auto_apply=False,
            reason='no_reliable_candidate',
            evidence_strength='insufficient',
            uncertainty_flags=['no_candidate_evidence'],
            recommended_action='Do not act automatically. Collect more evidence first.',
        )

    if candidate_count > 1 and gap < 2:
        uncertainty.append('narrow_candidate_gap')
    if high_risk:
        uncertainty.append('high_risk_change')

    if explicit_instruction:
        lane = 'safe_to_apply' if not high_risk else 'likely_but_review'
        return DecisionAssessment(
            lane=lane,
            confidence='high' if lane == 'safe_to_apply' else 'medium',
            can_auto_apply=lane == 'safe_to_apply',
            reason='explicit_user_instruction',
            evidence_strength='strong',
            uncertainty_flags=uncertainty,
            recommended_action='Apply the instructed mapping and keep the generated evidence bundle for review.',
        )

    if top_score >= 6 and (candidate_count == 1 or gap >= 2):
        return DecisionAssessment(
            lane='safe_to_apply',
            confidence='high',
            can_auto_apply=True,
            reason='single_strong_candidate',
            evidence_strength='strong',
            uncertainty_flags=uncertainty,
            recommended_action='Apply the strongest mapping automatically and record the rationale.',
        )

    if high_risk and requires_complete_mapping:
        return DecisionAssessment(
            lane='ambiguous' if candidate_count > 1 else 'likely_but_review',
            confidence=confidence,
            can_auto_apply=False,
            reason='high_risk_requires_review',
            evidence_strength='moderate' if top_score >= 0.7 else 'insufficient',
            uncertainty_flags=uncertainty or ['high_risk_change'],
            recommended_action='Stop before outward application and request review.',
        )

    if top_score >= 4:
        return DecisionAssessment(
            lane='likely_but_review' if gap >= 1 else 'ambiguous',
            confidence=confidence,
            can_auto_apply=False,
            reason='partial_but_not_safe',
            evidence_strength='moderate',
            uncertainty_flags=uncertainty or ['candidate_overlap'],
            recommended_action='Present the best candidates, but do not auto-apply them.',
        )

    return DecisionAssessment(
        lane='abstain',
        confidence='low',
        can_auto_apply=False,
        reason='weak_candidate_evidence',
        evidence_strength='insufficient',
        uncertainty_flags=uncertainty or ['weak_candidate_evidence'],
        recommended_action='Avoid automatic action and ask for more evidence or user guidance.',
    )


def lane_sort_key(lane: str) -> int:
    """Lane sort key.

    Args:
        lane: Primary lane used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    order = {
        'abstain': 0,
        'user_input_required': 1,
        'ambiguous': 2,
        'likely_but_review': 3,
        'safe_to_apply': 4,
    }
    return order.get(lane, -1)


def summarize_assessments(items: list[DecisionAssessment]) -> dict[str, Any]:
    """Summarize assessments.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        items: Primary items used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    counts: dict[str, int] = {}
    for item in items:
        counts[item.lane] = counts.get(item.lane, 0) + 1
    safest_lane = min((lane_sort_key(item.lane), item.lane) for item in items)[1] if items else 'abstain'
    return {
        'decision_counts': counts,
        'safest_overall_lane': safest_lane,
        'all_safe_to_apply': bool(items) and all(item.can_auto_apply for item in items),
    }
