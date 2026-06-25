"""Service helpers for securify.adapter.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from securify.tools.canonical_graph import persist_securify_graph
from securify.tools.scanner import inspect_target_security, render_markdown, scan_target_security


class SecurifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for securify workflows.
    """
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        """Initialize SecurifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('securify', root)

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
            payload = scan_target_security(target)
            payload['target_repo_id'] = tgt_id
            graph_bundle = persist_securify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['unit_index']['units']), 'relation_count': len(graph_bundle['relation_graph']['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=render_markdown(payload),
                role_prefix='securify_audit',
            )
            self._finish_run(run_id, 'ok', {
                'target_repo_id': tgt_id,
                'security_ok': payload['security_ok'],
                'risky_file_count': payload['risky_file_count'],
                'secret_hit_count': payload['secret_hit_count'],
                'canonical_graph': payload['canonical_graph'],
            })
            return self._attach_status_page('audit', {
                'ok': True,
                'suite': self.suite,
                'run_id': run_id,
                'security_ok': payload['security_ok'],
                'risky_file_count': payload['risky_file_count'],
                'secret_hit_count': payload['secret_hit_count'],
                'canonical_graph': payload['canonical_graph'],
                'summary': payload['summary'],
                'next_steps': payload['next_steps'],
                **paths,
            })
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return self._attach_status_page('audit', {'ok': False, 'suite': self.suite, 'run_id': run_id, 'reason': 'audit_failed', 'error': str(exc)})

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
        out['focus'] = ['security docs', 'secret exposure', 'ignore rules', 'plain-language remediation', 'security context packs']
        out['suite_role'] = 'Evaluate outward repository security hygiene and explain the next steps in readable language.'
        return out

    def explain(self, audience: str = 'developer') -> dict:
        """Explain the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            audience: Free-text input that shapes this operation.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        out = super().explain(audience)
        if out.get('ok'):
            out['suite_context'] = {
                'position_in_mvp': 'Securify is the security lane for the fy suites. It complements contract, documentation, usability, and testing work by making security risks visible before outward work proceeds.',
                'works_with': ['contractify', 'testify', 'documentify', 'docify', 'usabilify'],
            }
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
            'remove secret-like files from tracked surfaces and rotate any exposed values',
            'add a SECURITY.md or security guide that explains reporting and handling expectations',
            'add .gitignore rules for .env, *.pem, *.key, and similar secret-carrying files',
            'rerun securify after cleanup to verify that direct exposure surfaces are gone',
        ]
        return out

    def triage(self, query: str | None = None) -> dict:
        """Triage the requested operation.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        out = super().triage(query)
        out['triage_axes'] = ['direct secret exposure', 'security guidance', 'scope leakage', 'ignore protections', 'repo follow-up order']
        return out

    def prepare_context_pack(self, query: str, audience: str = 'developer') -> dict:
        """Prepare context pack.

        Args:
            query: Free-text input that shapes this operation.
            audience: Free-text input that shapes this operation.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        out = super().prepare_context_pack(query, audience)
        out['security_lens'] = 'Use the context pack to connect secret exposure, missing guidance, and nearby suite findings before deciding on outward remediation.'
        return out
