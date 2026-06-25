"""Tests for multi repo production stability.

"""
from __future__ import annotations

from pathlib import Path

from contractify.adapter.service import ContractifyAdapter
from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.ai.workspace import workspace_root


def test_contractify_can_bind_and_audit_multiple_target_repositories(tmp_path: Path) -> None:
    """Verify that contractify can bind and audit multiple target
    repositories works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo_a = create_target_repo(tmp_path / 'a')
    repo_b = create_target_repo(tmp_path / 'b')
    workspace = workspace_root(Path(__file__))
    adapter = ContractifyAdapter(workspace)
    init_a = adapter.init(str(repo_a))
    audit_a = adapter.audit(str(repo_a))
    init_b = adapter.init(str(repo_b))
    audit_b = adapter.audit(str(repo_b))
    assert init_a['ok'] is True and init_b['ok'] is True
    assert audit_a['ok'] is True and audit_b['ok'] is True
    compare = adapter.compare_runs(audit_a['run_id'], audit_b['run_id'])
    assert compare['ok'] is True
    assert 'target_repo_changed_between_runs' in compare['warnings'] or compare['target_repo_id_changed'] is True
