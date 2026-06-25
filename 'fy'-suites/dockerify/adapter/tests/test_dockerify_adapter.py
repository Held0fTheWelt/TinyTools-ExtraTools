"""Tests for dockerify adapter.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from dockerify.adapter.service import DockerifyAdapter


def test_dockerify_adapter_audit(tmp_path, monkeypatch):
    """Verify that dockerify adapter audit works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DockerifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
