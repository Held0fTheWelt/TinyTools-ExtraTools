"""Tests for model router quality.

"""
from fy_platform.ai.model_router.router import ModelRouter


def test_model_router_escalates_on_ambiguity() -> None:
    """Verify that model router escalates on ambiguity works as expected.
    """
    # Wire together the shared services that test_model_router_escalates_on_ambiguity
    # depends on for the rest of its workflow.
    router = ModelRouter()
    decision = router.route('triage', ambiguity='high', evidence_strength='moderate')
    assert decision.selected_tier == 'llm'
    assert 'ambiguity_escalation' in decision.reason
    assert decision.fallback_chain


def test_model_router_downgrades_when_evidence_is_weak() -> None:
    """Verify that model router downgrades when evidence is weak works as
    expected.
    """
    router = ModelRouter()
    decision = router.route('prepare_fix', ambiguity='low', evidence_strength='weak')
    assert decision.selected_tier == 'slm'
    assert decision.safety_mode == 'abstain-first'
