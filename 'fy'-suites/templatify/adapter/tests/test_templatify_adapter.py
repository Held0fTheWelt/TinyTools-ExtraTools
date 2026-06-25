"""Tests for templatify adapter.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from templatify.adapter.service import TemplatifyAdapter


def test_templatify_adapter_audit_generates_previews(tmp_path, monkeypatch):
    """Verify that templatify adapter audit generates previews works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = TemplatifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['template_count'] >= 3
    assert audit['drift_count'] == 0
    assert 'preview_dir' in audit
