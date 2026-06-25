"""Tests for graph recipes.

"""
from fy_platform.ai.graph_recipes import run_context_pack_recipe, run_inspect_recipe, run_triage_recipe
from fy_platform.tests.fixtures_autark import create_target_repo
from docify.adapter.service import DocifyAdapter


def test_graph_recipes_wrap_adapter_flows(tmp_path, monkeypatch):
    """Verify that graph recipes wrap adapter flows works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DocifyAdapter()
    adapter.audit(str(repo))
    inspect_result = run_inspect_recipe(adapter, 'docstring')
    assert inspect_result.ok is True
    triage_result = run_triage_recipe(adapter, 'missing docstrings')
    assert triage_result.ok is True
    pack_result = run_context_pack_recipe(adapter, 'docstring', 'developer')
    assert pack_result.ok is True
    assert pack_result.output['hit_count'] >= 1
