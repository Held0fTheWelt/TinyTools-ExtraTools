"""Tests for postmanify adapter.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from postmanify.adapter.service import PostmanifyAdapter


def test_postmanify_adapter_generates_collections(tmp_path, monkeypatch):
    """Verify that postmanify adapter generates collections works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = PostmanifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['sub_suite_count'] >= 1
