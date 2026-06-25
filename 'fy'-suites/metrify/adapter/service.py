"""Service helpers for metrify.adapter.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from metrify.tools.canonical_graph import persist_metrify_graph
from metrify.tools.ai_support import write_ai_pack
from metrify.tools.ledger import ensure_ledger
from metrify.tools.observify_bridge import write_observify_summary
from metrify.tools.reporting import build_summary, render_markdown, write_report_bundle


class MetrifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for metrify workflows.
    """
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        """Initialize MetrifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('metrify', root)

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
            # Build filesystem locations and shared state that the rest of audit reuses.
            ledger_path = self.hub_dir / 'state' / 'ledger.jsonl'
            ensure_ledger(ledger_path)
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            summary = build_summary(ledger_path)
            graph_bundle = persist_metrify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=summary)
            summary['canonical_graph'] = {'unit_count': len(graph_bundle['unit_index']['units']), 'relation_count': len(graph_bundle['relation_graph']['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            write_report_bundle(self.root, summary)
            write_ai_pack(self.root, summary)
            write_observify_summary(self.root, summary)
            # Read and normalize the input data before audit branches on or transforms
            # it further.
            md = render_markdown(summary)
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=summary, summary_md=md, role_prefix='metrify_audit')
            self._finish_run(run_id, 'ok', {'target_repo_id': tgt_id, 'event_count': summary.get('event_count', 0)})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'target_repo_id': tgt_id, 'canonical_graph': summary['canonical_graph'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
