"""Tests for models.

"""
from contractify.tools.models import automation_tier


def test_automation_tier_thresholds() -> None:
    """Verify that automation tier thresholds works as expected.
    """
    assert automation_tier(0.95) == "auto_high"
    assert automation_tier(0.75) == "curator_review"
    assert automation_tier(0.4) == "candidate_only"
