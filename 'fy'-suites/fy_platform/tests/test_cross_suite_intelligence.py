"""Tests for cross suite intelligence.

"""
from contractify.adapter.service import ContractifyAdapter
from fy_platform.ai.cross_suite_intelligence import collect_cross_suite_signals
from fy_platform.tests.fixtures_autark import create_target_repo
from testify.adapter.service import TestifyAdapter


def test_cross_suite_signals_connect_related_suite_runs(tmp_path, monkeypatch):
    """Verify that cross suite signals connect related suite runs works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    contractify = ContractifyAdapter()
    testify = TestifyAdapter()
    contractify.audit(str(repo))
    testify.audit(str(repo))
    signals = collect_cross_suite_signals(contractify.root, 'contractify', query='tests and adr reflection')
    assert signals['signal_count'] >= 1
    suites = {item['suite'] for item in signals['signals']}
    assert 'testify' in suites
