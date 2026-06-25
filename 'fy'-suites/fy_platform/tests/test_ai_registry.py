"""Tests for ai registry.

"""
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.semantic_index.index_manager import SemanticIndex


def test_registry_roundtrip(tmp_path, monkeypatch):
    """Verify that registry roundtrip works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    ws = tmp_path / "'fy'-suites"
    (ws / 'fy_platform').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (ws / 'fy_governance_enforcement.yaml').write_text('governance: true\n', encoding='utf-8')
    reg = EvidenceRegistry(ws)
    run = reg.start_run(suite='contractify', mode='audit', target_repo_root='/tmp/repo', target_repo_id='toy')
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    reg.record_artifact(suite='contractify', run_id=run.run_id, format='json', role='audit_json', path="reports/out.json", payload={'ok': True})
    latest = reg.latest_run('contractify')
    assert latest is not None
    assert latest['run_id'] == run.run_id
    assert reg.artifacts_for_run(run.run_id)


def test_semantic_index_search(tmp_path, monkeypatch):
    """Verify that semantic index search works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    ws = tmp_path / "'fy'-suites"
    (ws / 'fy_platform').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (ws / 'fy_governance_enforcement.yaml').write_text('governance: true\n', encoding='utf-8')
    index = SemanticIndex(ws)
    index.index_texts(suite='documentify', items=[('doc.md', 'runtime governance and testing'), ('two.md', 'postman collections from openapi')], scope='suite')
    hits = index.search('openapi collections', suite_scope=['documentify'])
    assert hits
    assert 'two.md' in hits[0].source_path
