"""Service helpers for postmanify.adapter.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from postmanify.tools.canonical_graph import persist_postmanify_graph
from fy_platform.ai.workspace import write_json
from postmanify.tools.openapi_postman import build_collections, load_openapi_dict


class PostmanifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for postmanify workflows.
    """
    __test__ = False
    def __init__(self, root: Path | None = None) -> None:
        """Initialize PostmanifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('postmanify', root)

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        This callable writes or records artifacts as part of its
        workflow. The implementation iterates over intermediate items
        before it returns.

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
            openapi = target / 'docs' / 'api' / 'openapi.yaml'
            # Branch on not openapi.is_file() so audit only continues along the matching
            # state path.
            if not openapi.is_file():
                raise FileNotFoundError(f'Missing OpenAPI file: {openapi}')
            # Build filesystem locations and shared state that the rest of audit reuses.
            spec = load_openapi_dict(openapi)
            master, subs = build_collections(spec, backend_api_prefix='/api/v1')
            generated_dir = self.hub_dir / 'generated' / tgt_id / run_id / 'postman'
            generated_dir.mkdir(parents=True, exist_ok=True)
            # Build filesystem locations and shared state that the rest of audit reuses.
            master_path = generated_dir / 'master_collection.json'
            # Persist the structured JSON representation so automated tooling can
            # consume the result without reparsing prose.
            write_json(master_path, master)
            sub_paths = []
            # Process (slug, coll) one item at a time so audit applies the same rule
            # across the full collection.
            for slug, coll in subs.items():
                path = generated_dir / f'{slug}.postman_collection.json'
                # Persist the structured JSON representation so automated tooling can
                # consume the result without reparsing prose.
                write_json(path, coll)
                sub_paths.append(str(path.relative_to(self.root)))
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            payload = {'openapi': str(openapi), 'sub_suite_count': len(subs), 'master_path': str(master_path.relative_to(self.root)), 'sub_paths': sub_paths}
            graph_bundle = persist_postmanify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['unit_index']['units']), 'relation_count': len(graph_bundle['relation_graph']['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            md = '# Postmanify Audit\n\n' + f'- openapi: `{openapi}`\n- sub_suite_count: {len(subs)}\n'
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='postmanify_audit')
            self._finish_run(run_id, 'ok', {'sub_suite_count': len(subs), 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'sub_suite_count': len(subs), 'canonical_graph': payload['canonical_graph'], **paths, 'generated_dir': str(generated_dir)}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
