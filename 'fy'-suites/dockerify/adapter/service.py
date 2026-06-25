"""Service helpers for dockerify.adapter.

"""
from __future__ import annotations

from pathlib import Path

from dockerify.tools.docker_audit import audit_docker_surface, render_markdown
from fy_platform.ai.base_adapter import BaseSuiteAdapter
from dockerify.tools.canonical_graph import persist_dockerify_graph


class DockerifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for dockerify workflows.
    """
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        """Initialize DockerifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('dockerify', root)

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        Exceptions are normalized inside the implementation before
        control returns to callers.

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
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            payload = audit_docker_surface(target)
            graph_bundle = persist_dockerify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['unit_index']['units']), 'relation_count': len(graph_bundle['relation_graph']['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            md = render_markdown(payload)
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='dockerify_audit')
            findings = len(payload.get('findings', [])) if isinstance(payload, dict) else 0
            self._finish_run(run_id, 'ok', {'finding_count': findings, 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': findings, 'canonical_graph': payload['canonical_graph'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
