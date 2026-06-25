"""Tests for phase58 transition and packaging.

"""
from __future__ import annotations

import json
from pathlib import Path

from despaghettify.adapter.service import DespaghettifyAdapter
from fy_platform.ai.production_readiness import render_workspace_production_markdown, workspace_production_readiness
from fy_platform.ai.release_readiness import render_workspace_release_markdown, workspace_release_readiness
from fy_platform.ai.status_page import render_status_markdown
from fy_platform.tools.cli import main


def _workspace_root() -> Path:
    """Workspace root.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[2]


def test_phase58_core_transition_profile_and_thinned_base_adapter() -> None:
    """Verify that phase58 core transition profile and thinned base adapter
    works as expected.
    """
    workspace = _workspace_root()
    adapter = DespaghettifyAdapter(root=workspace)
    audit = adapter.audit(str(workspace))
    assert audit['ok'] is True
    assert audit['transition_profile'] == 'core_transition'

    # Build filesystem locations and shared state that the rest of
    # test_phase58_core_transition_profile_and_thinned_base_adapter reuses.
    payload_path = workspace / audit['json_path']
    payload = json.loads(payload_path.read_text(encoding='utf-8'))
    assert payload['ownership_hotspots']
    assert 'refattening_guard_report' in payload
    line_count = sum(1 for _ in (workspace / 'fy_platform' / 'ai' / 'base_adapter.py').open(encoding='utf-8'))
    assert line_count < 350


def test_phase58_standard_reports_use_templated_rendering() -> None:
    """Verify that phase58 standard reports use templated rendering works
    as expected.
    """
    workspace = _workspace_root()
    status_md = render_status_markdown({
        'suite': 'contractify',
        'command': 'inspect',
        'ok': True,
        'summary': 'templated summary',
        'decision_summary': 'templated decision',
        'latest_run': {'run_id': 'r1', 'mode': 'audit', 'status': 'ok'},
        'next_steps': ['one'],
        'key_signals': {'finding_count': 1},
        'warnings': [],
        'cross_suite': {'signals': []},
        'governance': {'failures': [], 'warnings': []},
        'uncertainty': [],
    }, workspace)
    assert 'templify:template_id=reports:status_summary' in status_md

    release_md = render_workspace_release_markdown(workspace_release_readiness(workspace), workspace)
    assert 'templify:template_id=reports:workspace_release_readiness' in release_md

    production_md = render_workspace_production_markdown(workspace_production_readiness(workspace), workspace)
    assert 'templify:template_id=reports:workspace_production_readiness' in production_md


def test_phase58_platform_generate_surface_aliases_and_packaging_prep(capsys) -> None:
    """Verify that phase58 platform generate surface aliases and packaging
    prep works as expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace_root()
    rc = main(['generate', '--mode', 'surface_aliases', '--project-root', str(workspace)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['entry_count'] >= 1
    assert (workspace / payload['md_path']).is_file()

    rc = main(['generate', '--mode', 'packaging_prep', '--project-root', str(workspace)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['compatibility_impact_matrix']
    assert (workspace / payload['md_path']).is_file()
