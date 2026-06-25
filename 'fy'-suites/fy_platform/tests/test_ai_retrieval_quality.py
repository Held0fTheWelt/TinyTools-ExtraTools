"""Tests for ai retrieval quality.

"""
from fy_platform.ai.semantic_index.index_manager import SemanticIndex


def test_semantic_index_returns_richer_hit_metadata(tmp_path, monkeypatch) -> None:
    """Verify that semantic index returns richer hit metadata works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    # Wire together the shared services that
    # test_semantic_index_returns_richer_hit_metadata depends on for the rest of its
    # workflow.
    index = SemanticIndex(tmp_path)
    index.index_texts(
        suite='contractify',
        items=[('reports/contract.md', 'ADR health contract mapping and reflection summary')],
        scope='suite',
    )
    index.index_texts(
        suite='testify',
        items=[('reports/tests.md', 'health contract tests mirror ADR reflection requirements')],
        scope='suite',
    )
    hits = index.search('health contract reflection', limit=5)
    assert hits
    top = hits[0]
    assert top.matched_terms
    assert top.confidence in {'medium', 'high'}
    assert top.rationale
    pack = index.build_context_pack('health contract reflection', audience='developer')
    assert pack.evidence_confidence in {'medium', 'high'}
    assert pack.priorities
    assert pack.next_steps
