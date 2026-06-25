"""Tests for securify adapter.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from securify.adapter.service import SecurifyAdapter


def test_securify_adapter_audit_reports_security_followups(tmp_path, monkeypatch):
    """Verify that securify adapter audit reports security followups works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = SecurifyAdapter()
    result = adapter.audit(str(repo))
    assert result['ok'] is True
    assert 'security_ok' in result
    assert 'next_steps' in result
