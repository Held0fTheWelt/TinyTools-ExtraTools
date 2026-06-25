"""Tests for ai decision policy.

"""
from fy_platform.ai.decision_policy import assess_solution_decision


def test_decision_policy_safe_to_apply() -> None:
    """Verify that decision policy safe to apply works as expected.
    """
    decision = assess_solution_decision(
        explicit_instruction=False,
        candidate_count=1,
        top_score=8.0,
        second_score=0.0,
        high_risk=False,
    )
    assert decision.lane == 'safe_to_apply'
    assert decision.can_auto_apply is True


def test_decision_policy_requires_user_input() -> None:
    """Verify that decision policy requires user input works as expected.
    """
    decision = assess_solution_decision(
        explicit_instruction=False,
        candidate_count=0,
        top_score=0.0,
        second_score=0.0,
        high_risk=True,
        requires_complete_mapping=True,
        missing_required_mapping=True,
    )
    assert decision.lane == 'user_input_required'
    assert decision.can_auto_apply is False


def test_decision_policy_ambiguous_high_risk() -> None:
    """Verify that decision policy ambiguous high risk works as expected.
    """
    decision = assess_solution_decision(
        explicit_instruction=False,
        candidate_count=2,
        top_score=6.0,
        second_score=5.5,
        high_risk=True,
        requires_complete_mapping=True,
    )
    assert decision.lane in {'ambiguous', 'likely_but_review'}
    assert decision.can_auto_apply is False
