"""Tests for self hosting tracking and docs.

"""
from __future__ import annotations

import json
from pathlib import Path

from documentify.tools.track_engine import generate_track_bundle
from fy_platform.ai.self_hosting_tracking import build_self_hosting_tracking_snapshot
from fy_platform.ai.workspace import workspace_root
from fy_platform.tools.cli import main


def _workspace() -> Path:
    """Workspace the requested operation.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace_root(Path(__file__))


def test_self_hosting_tracking_snapshot_reports_real_layers() -> None:
    """Verify that self hosting tracking snapshot reports real layers works
    as expected.
    """
    tracking = build_self_hosting_tracking_snapshot(_workspace())
    assert tracking['tracked_suite_count'] >= 10
    assert tracking['active_suite_count'] >= 5
    assert tracking['tracking_layers']['runs']['exists'] is True
    assert tracking['tracking_layers']['graph_runs']['exists'] is True
    assert any(row['suite'] == 'documentify' and (row['run_count'] >= 1 or row['generated_target_count'] >= 1) for row in tracking['suite_rows'])


def test_documentify_self_hosting_outputs_are_generated(tmp_path) -> None:
    """Verify that documentify self hosting outputs are generated works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    workspace = _workspace()
    out_dir = tmp_path / 'generated'
    manifest = generate_track_bundle(workspace, out_dir, maturity='cross-linked')
    assert manifest['generated_count'] >= 1
    assert (out_dir / 'technical' / 'SELF_HOSTING_TRACKING.md').is_file()
    assert (out_dir / 'technical' / 'SELF_HOSTING_CONTRACTS.md').is_file()
    assert (out_dir / 'technical' / 'SELF_HOSTING_EVIDENCE.md').is_file()
    assert (out_dir / 'status' / 'SELF_HOSTING_HEALTH.md').is_file()
    ai_bundle = json.loads((out_dir / 'ai-read' / 'bundle.json').read_text(encoding='utf-8'))
    ids = {chunk['id'] for chunk in ai_bundle['chunks']}
    assert {'self_hosting_tracking', 'self_hosting_contracts', 'self_hosting_active_suites'} <= ids


def test_public_docs_surface_keeps_working_for_self_hosting_repo(capsys) -> None:
    """Verify that public docs surface keeps working for self hosting repo
    works as expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    code = main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(workspace)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    generated_dir = Path(payload['generated_dir'])
    assert (generated_dir / 'technical' / 'SELF_HOSTING_TRACKING.md').is_file()
