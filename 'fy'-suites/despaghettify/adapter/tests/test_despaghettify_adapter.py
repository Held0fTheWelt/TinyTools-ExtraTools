"""Tests for despaghettify adapter.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from despaghettify.adapter.service import DespaghettifyAdapter


def test_despaghettify_adapter_detects_spikes_and_reset(tmp_path, monkeypatch):
    """Verify that despaghettify adapter detects spikes and reset works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    # create a local spike file
    spike = repo / 'src' / 'spike.py'
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    spike.write_text('\n'.join(['x = 1'] * 400), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    adapter = DespaghettifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    assert audit['local_spike_count'] >= 1
    reset = adapter.reset('reindex-reset')
    assert reset['ok'] is True
