"""Tests for documentation drift.

"""
from __future__ import annotations

from docify.tools.documentation_drift import classify_repository_path, infer_hints


def test_classify_repository_path_routes() -> None:
    """Verify that classify repository path routes works as expected.
    """
    hint = classify_repository_path("backend/app/api/v1/example_routes.py")
    assert "http_or_public_api_surface" in hint.change_classes
    assert "LOCAL_DOCSTRINGS" in hint.recommended_documentation_layers


def test_classify_repository_path_docify_self() -> None:
    """Verify that classify repository path docify self works as expected.
    """
    hint = classify_repository_path("'fy'-suites/docify/tools/hub_cli.py")
    assert "docify_suite_self" in hint.change_classes
    assert "SUITE_README_OR_TOOL_DOCS" in hint.recommended_documentation_layers


def test_infer_hints_stable_order() -> None:
    """Verify that infer hints stable order works as expected.
    """
    hints = infer_hints(["b.py", "a.py"])
    paths = [h.path for h in hints]
    assert paths == ["a.py", "b.py"]
