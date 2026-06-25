"""Service helpers for documentify.adapter.

"""
from __future__ import annotations

from pathlib import Path

from documentify.tools.track_engine import generate_track_bundle
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DocumentifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for documentify workflows.
    """
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        """Initialize DocumentifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('documentify', root)

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        This callable writes or records artifacts as part of its
        workflow. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        # Protect the critical audit work so failures can be turned into a controlled
        # result or cleanup path.
        try:
            # Build filesystem locations and shared state that the rest of audit reuses.
            generated_dir = self.hub_dir / 'generated' / tgt_id / run_id
            generated_dir.mkdir(parents=True, exist_ok=True)
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            summary = generate_track_bundle(target, generated_dir, maturity='evidence-fill')
            graph_inputs = summary.get('graph_inputs', {})
            md = '# Documentify Generation\n\n' + f"- generated_count: {summary.get('generated_count', 0)}\n- generated_dir: `{generated_dir.relative_to(self.root)}`\n- tracks: {', '.join(summary.get('tracks', []))}\n- graph_mode: `{graph_inputs.get('shared_evidence_mode', 'heuristic-only')}`\n- docify_unit_count: {graph_inputs.get('docify', {}).get('unit_count', 0)}\n- normative_unit_count: {graph_inputs.get('contractify', {}).get('unit_count', 0)}\n- proof_unit_count: {graph_inputs.get('testify', {}).get('unit_count', 0)}\n"
            payload = {'summary': summary, 'generated_dir': str(generated_dir.relative_to(self.root))}
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='documentify_generation')
            self._finish_run(run_id, 'ok', {'doc_count': summary.get('generated_count', 0), 'target_repo_id': tgt_id, 'track_count': len(summary.get('tracks', [])), 'graph_mode': graph_inputs.get('shared_evidence_mode', 'heuristic-only')})
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            payload_out = {'ok': True, 'suite': self.suite, 'run_id': run_id, 'doc_count': summary.get('generated_count', 0), 'track_count': len(summary.get('tracks', [])), 'graph_inputs': graph_inputs, **paths, 'generated_dir': str(generated_dir), 'summary': 'Documentify generated the current documentation tracks and status pages.'}
            return self._attach_status_page('audit', payload_out)
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def inspect(self, query: str | None = None) -> dict:
        """Inspect the requested operation.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        out = super().inspect(query)
        out['tracks'] = ['easy', 'technical', 'role-admin', 'role-developer', 'role-operator', 'role-writer', 'role-player', 'ai-read']
        out['growth_ladder'] = ['inventory', 'skeleton', 'evidence-fill', 'cross-linked']
        return out

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        """Prepare fix.

        Args:
            finding_ids: Primary finding ids used by this step.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        out = super().prepare_fix(finding_ids)
        out['suggested_actions'] = [
            'grow document templates one maturity step upward via templatify-governed families',
            'cross-link generated documents to evidence sources',
            'export updated ai-read bundle for shared retrieval',
            'refresh INDEX.md and document manifest to reflect the new growth stage',
        ]
        return out
