"""Tests for contractify adapter.

"""
from contractify.adapter.service import ContractifyAdapter
from fy_platform.tests.fixtures_autark import create_target_repo


def test_contractify_adapter_full_cycle_and_consolidate(tmp_path, monkeypatch):
    """Verify that contractify adapter full cycle and consolidate works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = ContractifyAdapter()
    init = adapter.init(str(repo))
    assert init['ok'] is True
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    explain = adapter.explain()
    assert explain['ok'] is True
    pack = adapter.prepare_context_pack('openapi health')
    assert pack['hit_count'] >= 1

    consolidate = adapter.consolidate(str(repo), apply_safe=True)
    assert consolidate['ok'] is True
    assert consolidate['consolidated_adr_count'] >= 1
    assert consolidate['requires_user_input'] is False
    assert 'tests/adr_contract_matrix.py' in consolidate['applied_actions']
    assert (repo / 'tests' / 'adr_contract_matrix.py').is_file()
    assert (repo / 'tests' / 'test_adr_consolidation_alignment.py').is_file()
