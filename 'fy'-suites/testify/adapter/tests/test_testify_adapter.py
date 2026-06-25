"""Tests for testify adapter.

"""
from contractify.adapter.service import ContractifyAdapter
from fy_platform.tests.fixtures_autark import create_target_repo
from testify.adapter.service import TestifyAdapter


def test_testify_adapter_audit_and_compare_with_adr_reflection(tmp_path, monkeypatch):
    """Verify that testify adapter audit and compare with adr reflection
    works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    contractify = ContractifyAdapter()
    consolidate = contractify.consolidate(str(repo), apply_safe=True)
    assert consolidate['ok'] is True

    adapter = TestifyAdapter()
    first = adapter.audit(str(repo))
    second = adapter.audit(str(repo))
    assert first['ok'] and second['ok']
    assert first['adr_reflection']['consolidated_adr_count'] >= 1
    assert first['adr_reflection']['alignment_test_present'] is True
    assert not first['adr_reflection']['unmapped_adr_ids']
    diff = adapter.compare_runs(first['run_id'], second['run_id'])
    assert diff['ok'] is True
