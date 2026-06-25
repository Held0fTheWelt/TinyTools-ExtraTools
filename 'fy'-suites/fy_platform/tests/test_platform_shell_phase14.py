"""Tests for platform shell phase14.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.model_router.router import ModelRouter
from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.cli import main


def _workspace_root() -> Path:
    """Workspace root.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[2]


def test_platform_shell_analyze_contract_records_lanes_and_ir(tmp_path, capsys) -> None:
    """Verify that platform shell analyze contract records lanes and ir
    works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    workspace = _workspace_root()
    rc = main(['analyze', '--mode', 'contract', '--project-root', str(workspace), '--target-repo', str(repo)])
    assert rc == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_platform_shell_analyze_contract_records_lanes_and_ir.
    payload = json.loads(capsys.readouterr().out)
    assert payload['ok'] is True
    assert payload['compatibility_suite'] == 'contractify'
    assert payload['lane_execution_ids']
    assert payload['ir_refs']['snapshot_id']
    assert payload['ir_refs']['surface_alias_id']
    assert payload['ir_refs']['decision_id']

    # Build filesystem locations and shared state that the rest of
    # test_platform_shell_analyze_contract_records_lanes_and_ir reuses.
    lane_dir = workspace / '.fydata' / 'ir' / 'lane_executions'
    assert lane_dir.is_dir()
    assert any(path.suffix == '.json' for path in lane_dir.iterdir())


def test_platform_shell_govern_release_writes_platform_metadata(capsys) -> None:
    """Verify that platform shell govern release writes platform metadata
    works as expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace_root()
    rc = main(['govern', '--mode', 'release', '--project-root', str(workspace)])
    assert rc in {0, 3}
    payload = json.loads(capsys.readouterr().out)
    assert payload['public_command'] == 'govern'
    assert payload['mode_name'] == 'release'
    assert payload['platform_run_id']
    assert payload['lane_execution_ids']


def test_model_router_records_governor_fields_and_metrify_event(tmp_path) -> None:
    """Verify that model router records governor fields and metrify event
    works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    router = ModelRouter(tmp_path)
    decision = router.route('triage', ambiguity='high', evidence_strength='moderate')
    assert decision.selected_tier == 'llm'
    assert decision.governor_reason
    ledger_path = tmp_path / 'metrify' / 'state' / 'ledger.jsonl'
    assert ledger_path.is_file()
    lines = [json.loads(line) for line in ledger_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert lines
    assert 'guard_reason' in lines[-1]
    assert 'prompt_hash' in lines[-1]
