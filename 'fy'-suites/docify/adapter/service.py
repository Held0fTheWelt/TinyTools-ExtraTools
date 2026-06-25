"""Service helpers for docify.adapter.

"""
from __future__ import annotations

import ast
from pathlib import Path

from docify.tools.canonical_graph import persist_docify_graph
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DocifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for docify workflows.
    """
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        """Initialize DocifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('docify', root)

    def _scan_python(self, target: Path) -> dict:
        """Scan python.

        The implementation iterates over intermediate items before it
        returns. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            target: Primary target used by this step.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        # Assemble the structured result data before later steps enrich or return it
        # from _scan_python.
        findings = []
        scanned = 0
        # Process path one item at a time so _scan_python applies the same rule across
        # the full collection.
        for path in target.rglob('*.py'):
            parts = set(path.parts)
            # Branch on 'tests' in parts or '__pycache__' in parts or... so _scan_python
            # only continues along the matching state path.
            if 'tests' in parts or '__pycache__' in parts or '.venv' in parts:
                continue
            scanned += 1
            rel = path.relative_to(target).as_posix()
            # Protect the critical _scan_python work so failures can be turned into a
            # controlled result or cleanup path.
            try:
                module = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
            except SyntaxError:
                findings.append({'path': rel, 'line': 1, 'kind': 'module', 'name': '<module>', 'code': 'SYNTAX_ERROR'})
                continue
            # Branch on not ast.get_docstring(module) so _scan_python only continues
            # along the matching state path.
            if not ast.get_docstring(module):
                findings.append({'path': rel, 'line': 1, 'kind': 'module', 'name': '<module>', 'code': 'MISSING_MODULE_DOCSTRING'})
            # Process node one item at a time so _scan_python applies the same rule
            # across the full collection.
            for node in ast.walk(module):
                # Branch on isinstance(node, (ast.FunctionDef, ast.AsyncF... so
                # _scan_python only continues along the matching state path.
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Branch on node.name.startswith('_') and (not (node.name... so
                    # _scan_python only continues along the matching state path.
                    if node.name.startswith('_') and not (node.name.startswith('__') and node.name.endswith('__')):
                        continue
                    # Branch on not ast.get_docstring(node) so _scan_python only
                    # continues along the matching state path.
                    if not ast.get_docstring(node):
                        findings.append({'path': rel, 'line': int(getattr(node, 'lineno', 1)), 'kind': type(node).__name__.lower(), 'name': node.name, 'code': 'MISSING_DOCSTRING'})
        return {'scanned_python_files': scanned, 'findings': findings, 'finding_count': len(findings)}

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
        out['focus'] = ['docstring coverage', 'dense inline explanation', 'public API documentation', 'drift hints']
        out['suite_role'] = 'Improve Python documentation quality with stronger docstrings and richer inline explanations where code needs context.'
        return out

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
        try:
            payload = self._scan_python(target)
            graph_bundle = persist_docify_graph(workspace=self.root, repo_root=target, run_id=run_id, findings=payload['findings'])
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['units']), 'relation_count': len(graph_bundle['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            md_lines = ['# Docify Audit', '', f"- scanned_python_files: {payload['scanned_python_files']}", f"- finding_count: {payload['finding_count']}", f"- canonical_unit_count: {len(graph_bundle['units'])}", f"- canonical_relation_count: {len(graph_bundle['relations'])}", f"- canonical_artifact_count: {graph_bundle['artifact_index']['artifact_count']}", '']
            for finding in payload['findings'][:25]:
                md_lines.append(f"- `{finding['path']}:{finding['line']}` {finding['code']} — {finding['name']}")
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md='\n'.join(md_lines) + '\n', role_prefix='docify_audit')
            for relpath, role in [(graph_bundle['written_paths']['unit_index'][1], 'canonical_unit_index_json'), (graph_bundle['written_paths']['relation_graph'][1], 'canonical_relation_graph_json'), (graph_bundle['written_paths']['artifact_index'][1], 'canonical_artifact_index_json'), (graph_bundle['written_paths']['run_manifest'][1], 'canonical_run_manifest_json')]:
                self.registry.record_artifact(suite=self.suite, run_id=run_id, format='json', role=role, path=relpath, payload=(self.root / relpath).read_text(encoding='utf-8'))
            self._finish_run(run_id, 'ok', {'finding_count': payload['finding_count'], 'target_repo_id': tgt_id, 'canonical_unit_count': len(graph_bundle['units']), 'canonical_relation_count': len(graph_bundle['relations'])})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': payload['finding_count'], 'canonical_graph': payload['canonical_graph'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

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
            'add module/class/function docstrings for the highest-count files first',
            'prefer public API surfaces before private helpers',
            'use docify inline-explain for functions where the control flow is correct but too implicit for a reader',
            'group dense inline comments around responsibility blocks instead of scattering vague one-line remarks',
            'rerun docify audit to verify reduction',
        ]
        return out
