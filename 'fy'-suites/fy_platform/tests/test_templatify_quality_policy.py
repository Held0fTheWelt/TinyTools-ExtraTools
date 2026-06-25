"""Tests for templatify quality policy.

"""
from pathlib import Path

from fy_platform.ai.policy.suite_quality_policy import evaluate_suite_quality
from fy_platform.ai.workspace import workspace_root


def test_templatify_is_core_suite_and_quality_ready():
    """Verify that templatify is core suite and quality ready works as
    expected.
    """
    root = workspace_root(Path(__file__))
    quality = evaluate_suite_quality(root, 'templatify')
    assert quality['ok'] is True
