"""Tests for templatify.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.workspace import workspace_root
from templatify.tools.hub_cli import main
from templatify.tools.template_inventory import inspect_areas
from templatify.tools.templating_engine import apply_plan, build_plan


def test_inventory_detects_frontend(fake_repo: Path) -> None:
    """Verify that inventory detects frontend works as expected.

    Args:
        fake_repo: Primary fake repo used by this step.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_inventory_detects_frontend.
    payload = inspect_areas(fake_repo)
    frontend = payload['areas']['frontend']
    assert frontend['exists'] is True
    assert 'title' in frontend['base_blocks']
    assert frontend['child_count_extending_base'] == 1


def test_plan_generates_shell_and_adapter(fake_repo: Path) -> None:
    """Verify that plan generates shell and adapter works as expected.

    Args:
        fake_repo: Primary fake repo used by this step.
    """
    plan = build_plan(fake_repo, source_dir=fake_repo / 'source-pack')
    frontend = plan['areas']['frontend']
    assert frontend['status'] == 'ready'
    assert '{% block title %}' in frontend['generated_shell']
    assert '{% extends "_templatify/shell.html" %}' in frontend['generated_base']


def test_apply_preview_writes_generated_overlay(fake_repo: Path) -> None:
    """Verify that apply preview writes generated overlay works as
    expected.

    Args:
        fake_repo: Primary fake repo used by this step.
    """
    plan = build_plan(fake_repo, source_dir=fake_repo / 'source-pack', areas=['frontend'])
    written = apply_plan(fake_repo, plan, write_under_generated=True)
    shell_path = fake_repo / "'fy'-suites" / 'templatify' / 'generated' / 'frontend' / 'frontend' / 'templates' / '_templatify' / 'shell.html'
    base_path = fake_repo / "'fy'-suites" / 'templatify' / 'generated' / 'frontend' / 'frontend' / 'templates' / 'base.html'
    assert shell_path.is_file()
    assert base_path.is_file()
    assert any(path.endswith('_templatify/shell.html') for path in written)


def test_cli_plan_writes_reports(fake_repo: Path) -> None:
    """Verify that cli plan writes reports works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        fake_repo: Primary fake repo used by this step.
    """
    ws = workspace_root(Path(__file__))
    out = ws / 'templatify' / 'reports' / '_pytest_plan.json'
    md = ws / 'templatify' / 'reports' / '_pytest_plan.md'
    try:
        code = main(['plan', '--source-dir', str(fake_repo / 'source-pack'), '--areas', 'frontend', '--out', 'templatify/reports/_pytest_plan.json', '--md-out', 'templatify/reports/_pytest_plan.md', '--quiet'])
        assert code == 0
        payload = json.loads(out.read_text(encoding='utf-8'))
        assert payload['suite'] == 'templatify'
        assert md.is_file()
    finally:
        if out.exists():
            out.unlink()
        if md.exists():
            md.unlink()
