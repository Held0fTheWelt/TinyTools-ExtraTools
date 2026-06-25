"""Tests for template tooling.

"""
from pathlib import Path

from fy_platform.ai.workspace import workspace_root
from templatify.tools.template_registry import discover_templates
from templatify.tools.template_render import render_with_header
from templatify.tools.template_validator import validate_templates


def test_template_registry_and_validation_cover_families():
    """Verify that template registry and validation cover families works as
    expected.
    """
    root = workspace_root(Path(__file__))
    templates = discover_templates(root)
    validation = validate_templates(root)
    assert templates
    assert validation['ok'] is True
    assert 'documentify' in validation['families']


def test_template_render_includes_drift_header():
    """Verify that template render includes drift header works as expected.
    """
    root = workspace_root(Path(__file__))
    rendered, record = render_with_header(root, 'documentify', 'easy_overview', {'services_csv': 'backend, ai_stack'})
    assert rendered.startswith('<!-- templify:template_id=')
    assert record.template_id == 'documentify:easy_overview'
