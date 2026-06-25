"""Tests for production readiness cli.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.ai_suite_cli import main as suite_main
from fy_platform.tools.cli import main
from fy_platform.ai.workspace import workspace_root


def test_workspace_production_readiness_and_observability(tmp_path: Path, capsys) -> None:
    """Verify that workspace production readiness and observability works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    workspace = workspace_root(Path(__file__))
    assert suite_main(['contractify', 'audit', '--target-repo', str(repo)]) == 0
    _ = capsys.readouterr().out
    code = main(['production-readiness', '--project-root', str(workspace)])
    assert code in {0, 4}
    # Assemble the structured result data before later steps enrich or return it from
    # test_workspace_production_readiness_and_observability.
    payload = json.loads(capsys.readouterr().out)
    assert 'workspace_production_md_path' in payload
    assert payload['observability']['command_event_count'] >= 1
    obs_code = main(['observability-status', '--project-root', str(workspace)])
    assert obs_code == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_workspace_production_readiness_and_observability.
    obs_payload = json.loads(capsys.readouterr().out)
    assert obs_payload['command_event_count'] >= 1
