"""Tests for review policy and registry.

"""
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.policy.review_policy import validate_transition


def test_review_policy_rejects_invalid_transitions(tmp_path, monkeypatch):
    """Verify that review policy rejects invalid transitions works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    result = validate_transition('accepted', 'rejected')
    assert result.ok is False
    assert 'invalid_transition' in result.reason


def test_registry_compare_runs_and_evidence_review_state(tmp_path, monkeypatch):
    """Verify that registry compare runs and evidence review state works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    registry = EvidenceRegistry(tmp_path)
    run1 = registry.start_run(suite='contractify', mode='audit', target_repo_root='/tmp/one', target_repo_id='r1')
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    registry.record_artifact(suite='contractify', run_id=run1.run_id, format='json', role='audit_json', path='a.json', payload={'a': 1})
    ev = registry.record_evidence(suite='contractify', run_id=run1.run_id, kind='report', source_uri='reports/a.json', ownership_zone='fy', content_hash='abc', mime_type='application/json', deterministic=True)
    registry.finish_run(run1.run_id, status='ok')

    run2 = registry.start_run(suite='contractify', mode='audit', target_repo_root='/tmp/one', target_repo_id='r1')
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    registry.record_artifact(suite='contractify', run_id=run2.run_id, format='json', role='audit_json', path='a.json', payload={'a': 2})
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    registry.record_artifact(suite='contractify', run_id=run2.run_id, format='md', role='audit_md', path='a.md', payload={'md': True})
    registry.finish_run(run2.run_id, status='ok')

    delta = registry.compare_runs(run1.run_id, run2.run_id)
    assert delta is not None
    assert delta.artifact_delta == 1
    assert 'audit_md' in delta.added_roles

    transition = registry.update_evidence_review_state(ev.evidence_id, 'accepted')
    assert transition['ok'] is True
