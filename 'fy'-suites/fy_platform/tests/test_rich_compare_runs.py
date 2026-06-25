"""Tests for rich compare runs.

"""
from contractify.adapter.service import ContractifyAdapter
from fy_platform.tests.fixtures_autark import create_target_repo


def test_compare_runs_returns_richer_delta(tmp_path, monkeypatch):
    """Verify that compare runs returns richer delta works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = ContractifyAdapter()
    first = adapter.audit(str(repo))
    second = adapter.consolidate(str(repo), apply_safe=True)
    delta = adapter.compare_runs(first['run_id'], second['run_id'])
    assert delta['ok'] is True
    assert 'left_artifact_count' in delta
    assert 'right_artifact_count' in delta
    assert 'left_journal_event_count' in delta
    assert 'right_journal_event_count' in delta
    assert 'right_review_state_counts' in delta
