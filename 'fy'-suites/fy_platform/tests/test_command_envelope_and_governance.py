"""Tests for command envelope and governance.

"""
from fy_platform.ai.adapter_cli_helper import build_command_envelope
from fy_platform.tests.fixtures_autark import create_target_repo
from contractify.adapter.service import ContractifyAdapter


def test_command_envelope_classifies_success_and_failure(tmp_path, monkeypatch):
    """Verify that command envelope classifies success and failure works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = ContractifyAdapter()
    ok_env = build_command_envelope('contractify', 'init', adapter.init(str(repo)))
    assert ok_env.ok is True
    assert ok_env.exit_code == 0

    fail_env = build_command_envelope('contractify', 'init', adapter.init(str(repo / 'missing')))
    assert fail_env.ok is False
    assert fail_env.exit_code == 1
    assert fail_env.error_code == 'target_repo_not_found'


def test_suite_self_governance_status_is_reported(tmp_path, monkeypatch):
    """Verify that suite self governance status is reported works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = ContractifyAdapter()
    result = adapter.init(str(repo))
    assert result['ok'] is True
    assert result['governance']['ok'] is True
    assert 'warnings' in result['governance']
