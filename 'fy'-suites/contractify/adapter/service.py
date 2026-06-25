"""Service helpers for contractify.adapter.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from contractify.tools.audit_pipeline import build_discover_payload, run_audit
from contractify.tools.importer import import_contractify_bundle
from contractify.tools.canonical_graph import persist_contractify_graph
from contractify.tools.coda_exports import emit_contract_obligation_manifest
from fy_platform.ai.adr_reflection import (
    discover_consolidated_adrs,
    find_candidate_test_matches,
    parse_instruction_mapping,
    render_alignment_test_module,
    render_contract_matrix_module,
)
from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.decision_policy import assess_solution_decision, summarize_assessments
from fy_platform.ai.workspace import write_json, write_text


class ContractifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for contractify workflows.
    """
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        """Initialize ContractifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('contractify', root)

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
            # Protect the critical audit work so failures can be turned into a
            # controlled result or cleanup path.
            try:
                payload = run_audit(target, max_contracts=30)
            except Exception as exc:
                payload = {
                    'stats': {'contracts': 0, 'drift_findings': 0, 'conflicts': 0},
                    'drift_findings': [],
                    'conflicts': [],
                    'fallback_note': f'contractify fallback summary used: {exc}',
                    'discovery_preview': build_discover_payload(target, max_contracts=30) if target.exists() else {},
                }
            # Assemble the structured result data before later steps enrich or return it
            # from audit.
            findings = len(payload.get('drift_findings', [])) + len(payload.get('conflicts', []))
            graph_bundle = persist_contractify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['units']), 'relation_count': len(graph_bundle['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1], 'claim_count': graph_bundle['normative_inventory']['claim_count'], 'family_count': len(graph_bundle['normative_inventory'].get('family_counts', {}))}
            md = (
                '# Contractify Audit\n\n'
                f'- target: `{target}`\n'
                f'- findings: {findings}\n'
                f"- canonical_unit_count: {len(graph_bundle['units'])}\n"
                f"- canonical_relation_count: {len(graph_bundle['relations'])}\n"
                f"- canonical_claim_count: {graph_bundle['normative_inventory']['claim_count']}\n"
            )
            reports_root = self.root / 'contractify' / 'reports'
            reports_root.mkdir(parents=True, exist_ok=True)
            write_json(reports_root / 'audit_latest.json', payload)
            write_text(reports_root / 'contractify_audit_report_latest.md', md)
            emit_contract_obligation_manifest(self.root)
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=md, role_prefix='contractify_audit')
            # Process (relpath, role) one item at a time so audit applies the same rule
            # across the full collection.
            for relpath, role in [(graph_bundle['written_paths']['unit_index'][1], 'canonical_unit_index_json'), (graph_bundle['written_paths']['relation_graph'][1], 'canonical_relation_graph_json'), (graph_bundle['written_paths']['artifact_index'][1], 'canonical_artifact_index_json'), (graph_bundle['written_paths']['run_manifest'][1], 'canonical_run_manifest_json')]:
                self.registry.record_artifact(suite=self.suite, run_id=run_id, format='json', role=role, path=relpath, payload=(self.root / relpath).read_text(encoding='utf-8'))
            self._finish_run(run_id, 'ok', {'finding_count': findings, 'target_repo_id': tgt_id, 'canonical_claim_count': graph_bundle['normative_inventory']['claim_count'], 'canonical_contract_count': graph_bundle['normative_inventory']['contract_count']})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'finding_count': findings, 'canonical_graph': payload['canonical_graph'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def _smart_required_paths(self, candidates: list[dict[str, Any]]) -> list[str]:
        """Smart required paths.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            candidates: Primary candidates used by this step.

        Returns:
            list[str]:
                Collection produced from the parsed or
                accumulated input data.
        """
        if not candidates:
            return []
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        if top['score'] >= 6 and (second is None or top['score'] >= second['score'] + 2):
            return [top['path']]
        if top['score'] >= 6 and second and second['score'] >= 4:
            return [top['path'], second['path']]
        return []

    def _decision_for_adr(self, *, adr_id: str, candidates: list[dict[str, Any]], required_paths: list[str], explicit_instruction: bool) -> dict[str, Any]:
        """Decision for adr.

        Args:
            adr_id: Identifier used to select an existing run or record.
            candidates: Primary candidates used by this step.
            required_paths: Primary required paths used by this step.
            explicit_instruction: Whether to enable this optional
                behavior.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        top = candidates[0]['score'] if candidates else 0.0
        second = candidates[1]['score'] if len(candidates) > 1 else 0.0
        missing_required = not required_paths
        assessment = assess_solution_decision(
            explicit_instruction=explicit_instruction,
            candidate_count=len(candidates),
            top_score=top,
            second_score=second,
            high_risk=True,
            requires_complete_mapping=True,
            missing_required_mapping=missing_required,
        )
        return {
            'adr_id': adr_id,
            'lane': assessment.lane,
            'confidence': assessment.confidence,
            'can_auto_apply': assessment.can_auto_apply,
            'reason': assessment.reason,
            'evidence_strength': assessment.evidence_strength,
            'uncertainty_flags': assessment.uncertainty_flags,
            'recommended_action': assessment.recommended_action,
        }

    def _build_consolidation_plan(self, target: Path, audit_payload: dict[str, Any], instruction: str | None) -> dict[str, Any]:
        """Build consolidation plan.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            target: Primary target used by this step.
            audit_payload: Primary audit payload used by this step.
            instruction: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        instruction_map = parse_instruction_mapping(instruction)
        consolidated_adrs = discover_consolidated_adrs(target)
        entries: list[dict[str, Any]] = []
        user_questions: list[str] = []
        auto_actions: list[str] = []
        unresolved: list[str] = []
        smart_auto_resolved: list[str] = []
        assessments = []
        for adr in consolidated_adrs:
            candidates = find_candidate_test_matches(target, adr)
            required_paths = self._smart_required_paths(candidates)
            explicit_instruction = adr['adr_id'] in instruction_map
            if explicit_instruction:
                required_paths = instruction_map[adr['adr_id']]
            elif required_paths:
                smart_auto_resolved.append(adr['adr_id'])
            decision = self._decision_for_adr(
                adr_id=adr['adr_id'],
                candidates=candidates,
                required_paths=required_paths,
                explicit_instruction=explicit_instruction,
            )
            assessments.append(decision)
            if decision['lane'] in {'user_input_required', 'ambiguous', 'abstain'}:
                unresolved.append(adr['adr_id'])
                user_questions.append(
                    f"Provide explicit test path mappings for {adr['adr_id']} using --instruction 'ADR-xxxx=tests/test_file.py[,tests/test_other.py]'"
                )
            entries.append({
                'adr_id': adr['adr_id'],
                'title': adr['title'],
                'source_path': adr['path'],
                'keywords': adr['keywords'],
                'candidate_test_matches': candidates,
                'required_test_paths': required_paths,
                'decision': decision,
            })
        if entries:
            auto_actions.extend([
                'write tests/adr_contract_matrix.py',
                'write tests/test_adr_consolidation_alignment.py',
            ])
        rollup = summarize_assessments([assess_solution_decision(
            explicit_instruction=item['reason'] == 'explicit_user_instruction',
            candidate_count=1 if item['can_auto_apply'] else 2,
            top_score=0.9 if item['lane'] == 'safe_to_apply' else 0.5 if item['lane'] == 'likely_but_review' else 0.0,
            second_score=0.1,
            high_risk=item['lane'] != 'safe_to_apply',
            requires_complete_mapping=True,
            missing_required_mapping=item['lane'] in {'user_input_required', 'abstain'},
        ) for item in assessments])
        weakest_lane = rollup['safest_overall_lane']
        plan = {
            'consolidated_adrs': entries,
            'stats': {
                'consolidated_adr_count': len(entries),
                'drift_count': len(audit_payload.get('drift_findings', [])),
                'conflict_count': len(audit_payload.get('conflicts', [])),
                'unresolved_adr_count': len(unresolved),
                'smart_auto_resolved_count': len(smart_auto_resolved),
            },
            'smart_auto_resolved_adr_ids': smart_auto_resolved,
            'unresolved_adr_ids': unresolved,
            'requires_user_input': bool(unresolved),
            'user_questions': user_questions,
            'auto_actions': auto_actions,
            'instruction_used': instruction or '',
            'can_apply_safe': bool(entries) and all(item['decision']['can_auto_apply'] for item in entries),
            'decision': {
                'lane': weakest_lane,
                'recommended_action': 'Apply automatically only when every consolidated ADR is classified as safe_to_apply. Otherwise stop and ask for review or input.',
                'uncertainty_flags': sorted({flag for item in assessments for flag in item['uncertainty_flags']}),
                'decision_counts': rollup['decision_counts'],
            },
            'advisory_note': 'Contractify may safely apply generated ADR/test reflection scaffolding only when every consolidated ADR resolves to at least one explicit or strongly auto-resolved test path.',
        }
        return plan

    def consolidate(self, target_repo_root: str, *, apply_safe: bool = False, instruction: str | None = None) -> dict[str, Any]:
        """Consolidate the requested operation.

        This callable writes or records artifacts as part of its
        workflow. The implementation iterates over intermediate items
        before it returns.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.
            apply_safe: Whether to enable this optional behavior.
            instruction: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('consolidate', target)
        generated_dir = self.hub_dir / 'generated' / 'consolidations' / tgt_id / run_id
        generated_dir.mkdir(parents=True, exist_ok=True)
        try:
            try:
                audit_payload = run_audit(target, max_contracts=30)
            except Exception as exc:
                audit_payload = {
                    'drift_findings': [],
                    'conflicts': [],
                    'fallback_note': f'contractify consolidate fallback audit used: {exc}',
                }
            plan = self._build_consolidation_plan(target, audit_payload, instruction)
            applied_actions: list[str] = []
            matrix_rel = 'tests/adr_contract_matrix.py'
            alignment_rel = 'tests/test_adr_consolidation_alignment.py'
            if apply_safe and plan['can_apply_safe']:
                # Write the human-readable companion text so reviewers can inspect the
                # result without opening raw structured data.
                write_text(target / matrix_rel, render_contract_matrix_module(plan['consolidated_adrs']))
                # Write the human-readable companion text so reviewers can inspect the
                # result without opening raw structured data.
                write_text(target / alignment_rel, render_alignment_test_module())
                applied_actions.extend([matrix_rel, alignment_rel])
            elif apply_safe and not plan['can_apply_safe']:
                plan['apply_safe_blocked'] = True
            plan['applied_actions'] = applied_actions
            plan['target_repo_root'] = str(target)
            plan['target_repo_id'] = tgt_id
            plan['generated_preview_dir'] = str(generated_dir.relative_to(self.root))
            plan['uncertainty'] = list(plan['decision'].get('uncertainty_flags', []))

            md_lines = [
                '# Contractify Consolidate',
                '',
                f'- target: `{target}`',
                f"- consolidated ADRs: {plan['stats']['consolidated_adr_count']}",
                f"- smart auto-resolved ADRs: {plan['stats']['smart_auto_resolved_count']}",
                f"- unresolved ADRs: {plan['stats']['unresolved_adr_count']}",
                f"- can_apply_safe: {plan['can_apply_safe']}",
                f"- decision_lane: `{plan['decision']['lane']}`",
                f"- applied_actions: {len(applied_actions)}",
                '',
            ]
            for entry in plan['consolidated_adrs']:
                md_lines.append(
                    f"- {entry['adr_id']}: {entry['title']} -> {entry['required_test_paths'] or 'USER INPUT REQUIRED'} | lane={entry['decision']['lane']}"
                )
            if plan['user_questions']:
                md_lines.extend(['', '## User input required', ''])
                md_lines.extend(f'- {q}' for q in plan['user_questions'])
            md_text = '\n'.join(md_lines) + '\n'
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            write_text(generated_dir / 'contractify_consolidation_plan.md', md_text)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            write_text(
                generated_dir / 'contractify_consolidation_matrix_preview.py',
                render_contract_matrix_module(plan['consolidated_adrs']) if plan['consolidated_adrs'] else 'ADR_TEST_MATRIX = {}\n',
            )
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=plan, summary_md=md_text, role_prefix='contractify_consolidate')
            self._finish_run(
                run_id,
                'ok',
                {
                    'consolidated_adr_count': plan['stats']['consolidated_adr_count'],
                    'unresolved_adr_count': plan['stats']['unresolved_adr_count'],
                    'applied_action_count': len(applied_actions),
                    'target_repo_id': tgt_id,
                    'decision_lane': plan['decision']['lane'],
                },
            )
            return {
                'ok': True,
                'suite': self.suite,
                'run_id': run_id,
                'summary': 'Contractify consolidate now classifies each ADR/test reflection decision before any outward action. It applies changes only in narrowly safe cases and otherwise stops with clear next steps.',
                'consolidated_adr_count': plan['stats']['consolidated_adr_count'],
                'smart_auto_resolved_count': plan['stats']['smart_auto_resolved_count'],
                'requires_user_input': plan['requires_user_input'],
                'can_apply_safe': plan['can_apply_safe'],
                'applied_actions': applied_actions,
                'user_questions': plan['user_questions'],
                'decision': plan['decision'],
                'uncertainty': plan['uncertainty'],
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}

    def triage(self, query: str | None = None) -> dict:
        """Triage the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        base = super().triage(query)
        latest = self.registry.latest_run(self.suite)
        if latest:
            artifacts = self.registry.artifacts_for_run(latest['run_id'])
            base['latest_artifact_count'] = len(artifacts)
        return base

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
            're-anchor affected contracts to a single owner vocabulary',
            'refresh projection/back-reference links',
            'run contractify consolidate to generate ADR/test reflection scaffolding',
            'regenerate audit and compare against accepted run',
        ]
        return out


    def import_bundle(self, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
        """Import bundle.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            bundle_path: Filesystem path to the file or directory being
                processed.
            legacy: Whether to enable this optional behavior.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        bundle = Path(bundle_path).resolve()
        if not bundle.exists():
            return self._attach_status_page(
                'legacy-import' if legacy else 'import',
                {
                    'ok': False,
                    'suite': self.suite,
                    'reason': 'bundle_not_found',
                    'bundle_path': bundle_path,
                    'legacy': legacy,
                },
            )
        run_id, run_dir, _ = self._start_run('legacy-import' if legacy else 'import', self.root)
        try:
            payload = import_contractify_bundle(bundle, self.root, legacy=legacy)
            payload.update({
                'suite': self.suite,
                'run_id': run_id,
                'legacy': legacy,
                'summary': 'Contractify imported an external bundle into the current internal import lane without overwriting current workspace truth.',
            })
            summary_md = (
                '# Contractify Import\n\n'
                f"- bundle: `{bundle}`\n"
                f"- legacy: `{str(legacy).lower()}`\n"
                f"- artifact_count: {payload.get('artifact_count', 0)}\n"
            )
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=summary_md,
                role_prefix='contractify_legacy_import' if legacy else 'contractify_import',
            )
            self._finish_run(
                run_id,
                'ok',
                {'bundle_path': str(bundle), 'legacy': legacy, 'artifact_count': payload.get('artifact_count', 0)},
            )
            return {**payload, **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc), 'bundle_path': str(bundle), 'legacy': legacy})
            return self._attach_status_page(
                'legacy-import' if legacy else 'import',
                {
                    'ok': False,
                    'suite': self.suite,
                    'run_id': run_id,
                    'reason': 'import_failed',
                    'bundle_path': str(bundle),
                    'legacy': legacy,
                    'error': str(exc),
                    'recovery_hints': [
                        'Check that the bundle contains a contractify suite or importable docs/reports surfaces.',
                        'Use legacy-import for older or nested fy-suite bundles.',
                    ],
                },
            )
