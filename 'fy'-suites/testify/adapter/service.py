"""Service helpers for testify.adapter.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.adr_reflection import compute_reflection_status, discover_consolidated_adrs
from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.decision_policy import assess_solution_decision
from testify.tools.canonical_graph import persist_testify_graph
from testify.tools.test_governance import audit_test_governance, render_markdown


class TestifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for testify workflows.
    """
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        """Initialize TestifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('testify', root)

    def _latest_contractify_consolidation(self, target_repo_id: str) -> dict[str, Any] | None:
        """Latest contractify consolidation.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            target_repo_id: Identifier used to select an existing run or
                record.

        Returns:
            dict[str, Any] | None:
                Structured payload describing the
                outcome of the operation.
        """
        # Process run one item at a time so _latest_contractify_consolidation applies
        # the same rule across the full collection.
        for run in self.registry.list_runs('contractify'):
            # Branch on run.get('mode') != 'consolidate' so
            # _latest_contractify_consolidation only continues along the matching state
            # path.
            if run.get('mode') != 'consolidate':
                continue
            # Branch on run.get('target_repo_id') != target_repo_id so
            # _latest_contractify_consolidation only continues along the matching state
            # path.
            if run.get('target_repo_id') != target_repo_id:
                continue
            artifacts = self.registry.artifacts_for_run(run['run_id'])
            # Process artifact one item at a time so _latest_contractify_consolidation
            # applies the same rule across the full collection.
            for artifact in artifacts:
                # Branch on artifact.get('role') == 'contractify_consolid... so
                # _latest_contractify_consolidation only continues along the matching
                # state path.
                if artifact.get('role') == 'contractify_consolidate_json':
                    # Assemble the structured result data before later steps enrich or
                    # return it from _latest_contractify_consolidation.
                    payload = self.registry.artifact_payload(artifact['artifact_id'])
                    # Branch on isinstance(payload, dict) so
                    # _latest_contractify_consolidation only continues along the
                    # matching state path.
                    if isinstance(payload, dict):
                        return payload
        return None

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
            try:
                payload = audit_test_governance(target)
            except Exception as exc:
                checks = []
                checks.append({'name': 'tests_run_script', 'ok': (target / 'tests' / 'run_tests.py').is_file()})
                checks.append({'name': 'github_workflow', 'ok': any((target / '.github' / 'workflows').glob('*.y*ml')) if (target / '.github' / 'workflows').is_dir() else False})
                payload = {'fallback_note': f'testify fallback used: {exc}', 'checks': checks, 'findings': [c for c in checks if not c['ok']]}
            latest_contractify = self._latest_contractify_consolidation(tgt_id)
            consolidated_adrs = latest_contractify.get('consolidated_adrs', []) if latest_contractify else discover_consolidated_adrs(target)
            reflection = compute_reflection_status(target, consolidated_adrs)
            payload['adr_reflection'] = reflection
            payload['contractify_consolidation_available'] = bool(latest_contractify)
            payload.setdefault('findings', [])
            payload.setdefault('warnings', [])
            if reflection['consolidated_adr_count'] and not reflection['alignment_test_present']:
                payload['findings'].append({
                    'id': 'TESTIFY-ADR-CONSOLIDATION-ALIGNMENT-TEST-MISSING',
                    'severity': 'high',
                    'summary': 'Consolidated ADRs exist, but tests/test_adr_consolidation_alignment.py is missing.',
                })
            if reflection['unmapped_adr_ids']:
                payload['findings'].append({
                    'id': 'TESTIFY-ADR-TEST-REFLECTION-GAP',
                    'severity': 'high',
                    'summary': 'Consolidated ADRs are not mirrored in explicit test mappings: ' + ', '.join(reflection['unmapped_adr_ids']),
                })
            if reflection['weakly_mapped_adr_ids']:
                payload['warnings'].append('Weak ADR reflection detected for: ' + ', '.join(reflection['weakly_mapped_adr_ids']))
            md = render_markdown(payload)
            if reflection['consolidated_adr_count']:
                md += '\n## ADR reflection\n\n'
                md += f"- consolidated ADR count: `{reflection['consolidated_adr_count']}`\n"
                md += f"- alignment test present: `{reflection['alignment_test_present']}`\n"
                md += f"- mirrored ADR ids: `{reflection['mirrored_adr_ids']}`\n"
                md += f"- weakly mapped ADR ids: `{reflection['weakly_mapped_adr_ids']}`\n"
                md += f"- unmapped ADR ids: `{reflection['unmapped_adr_ids']}`\n"
            graph_bundle = persist_testify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['units']), 'relation_count': len(graph_bundle['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1], 'linked_claim_count': graph_bundle['claim_proof_status']['linked_claim_count'], 'linked_family_count': sum(1 for c in graph_bundle['claim_proof_status'].get('linked_claims_by_family', {}).values() if c > 0), 'contractify_graph_available': bool(graph_bundle['proof_report'].get('contractify_graph_available'))}
            md += f"\n## Canonical proof slice\n\n- linked claim count: `{graph_bundle['claim_proof_status']['linked_claim_count']}`\n- linked family count: `{sum(1 for c in graph_bundle['claim_proof_status'].get('linked_claims_by_family', {}).values() if c > 0)}`\n- contractify graph available: `{bool(graph_bundle['proof_report'].get('contractify_graph_available'))}`\n"
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='testify_audit')
            for relpath, role in [(graph_bundle['written_paths']['unit_index'][1], 'canonical_unit_index_json'), (graph_bundle['written_paths']['relation_graph'][1], 'canonical_relation_graph_json'), (graph_bundle['written_paths']['artifact_index'][1], 'canonical_artifact_index_json'), (graph_bundle['written_paths']['run_manifest'][1], 'canonical_run_manifest_json')]:
                self.registry.record_artifact(suite=self.suite, run_id=run_id, format='json', role=role, path=relpath, payload=(self.root / relpath).read_text(encoding='utf-8'))
            failures = len(payload.get('findings', [])) if isinstance(payload, dict) else 0
            decision = assess_solution_decision(
                explicit_instruction=False,
                candidate_count=max(reflection['consolidated_adr_count'] - len(reflection['unmapped_adr_ids']), 0),
                top_score=0.9 if not reflection['unmapped_adr_ids'] and reflection['alignment_test_present'] else 0.55 if reflection['weakly_mapped_adr_ids'] else 0.0,
                second_score=0.4 if reflection['weakly_mapped_adr_ids'] else 0.0,
                high_risk=bool(reflection['consolidated_adr_count']),
                requires_complete_mapping=True,
                missing_required_mapping=bool(reflection['unmapped_adr_ids']),
            )
            self._finish_run(run_id, 'ok', {'finding_count': failures, 'target_repo_id': tgt_id, 'consolidated_adr_count': reflection['consolidated_adr_count'], 'linked_claim_count': graph_bundle['claim_proof_status']['linked_claim_count']})
            return {
                'ok': True,
                'suite': self.suite,
                'run_id': run_id,
                'finding_count': failures,
                'adr_reflection': reflection,
                'canonical_graph': payload['canonical_graph'],
                'decision': {
                    'lane': decision.lane,
                    'recommended_action': decision.recommended_action,
                    'uncertainty_flags': decision.uncertainty_flags,
                },
                'uncertainty': list(decision.uncertainty_flags),
                'summary': 'Testify now checks not only whether tests run, but also whether consolidated ADRs are reflected in named tests and mappings.',
                **paths,
            }
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
            'align tests/run_tests.py with workflow entries',
            'ensure CI workflow covers required suite targets',
            'mirror consolidated ADRs in explicit ADR alignment tests and mappings',
            'refresh testify audit after changes',
        ]
        return out
