"""Canonical graph for securify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_securify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist securify graph.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        workspace: Primary workspace used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        run_id: Identifier used to select an existing run or record.
        payload: Structured data carried through this workflow.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    now = utc_now()
    units = []
    relations = []
    workflow_id = stable_unit_id('securify', 'workflow', 'securify-audit')
    units.append({'unit_id': workflow_id, 'title': 'securify audit', 'entity_type': 'workflow', 'owner_suite': 'securify', 'source_paths': ['securify/adapter/service.py', 'securify/tools/scanner.py'], 'summary': 'Audit workflow for repository security hygiene.', 'why_it_exists': 'Primary outward security governance workflow.', 'contracts': [], 'dependencies': [], 'consumers': ['developer','operator'], 'commands': ['analyze --mode security'], 'inputs': ['target_repo_root'], 'outputs': ['security-boundary-report','coverage-report'], 'failure_modes': [], 'evidence_refs': ['source:securify/adapter/service.py'], 'roles': ['developer','operator'], 'layer_status': {'technical': 'observed'}, 'maturity': 'cross-linked', 'last_verified': now, 'stability': 'observed', 'tags': ['security','workflow']})
    inventory = payload.get('inventory', {})
    policy_id = stable_unit_id('securify', 'policy-rule', 'secret-and-guidance-hygiene')
    units.append({'unit_id': policy_id, 'title': 'secret and guidance hygiene', 'entity_type': 'policy-rule', 'owner_suite': 'securify', 'source_paths': ['securify/README.md','securify/tools/scanner.py'], 'summary': 'Security guidance and secret exposure hygiene policy.', 'why_it_exists': 'Represents the minimum repository security hygiene expectation.', 'contracts': [], 'dependencies': [], 'consumers': ['developer','operator'], 'commands': [], 'inputs': [], 'outputs': ['security guidance'], 'failure_modes': [], 'evidence_refs': ['source:securify/README.md'], 'roles': ['developer','operator'], 'layer_status': {'technical':'observed'}, 'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['security','policy']})
    relations.append({'relation_id': stable_relation_id('securify', workflow_id, 'governs', policy_id), 'from_id': workflow_id, 'to_id': policy_id, 'relation_type': 'governs', 'owner_suite': 'securify', 'evidence_refs': ['source:securify/tools/scanner.py'], 'confidence': 'high', 'created_at': now, 'last_verified': now})
    # Process (name, exists) one item at a time so persist_securify_graph applies the
    # same rule across the full collection.
    for name, exists in [('security-doc-surface', inventory.get('security_doc_count',0)>0), ('secret-ignore-surface', inventory.get('ignore_has_secret_rules',False))]:
        uid = stable_unit_id('securify', 'runtime-surface', name)
        units.append({'unit_id': uid, 'title': name, 'entity_type': 'runtime-surface', 'owner_suite': 'securify', 'source_paths': [], 'summary': f'Security audit surface {name}.', 'why_it_exists': 'Observed security-relevant repository surface.', 'contracts': [], 'dependencies': [], 'consumers': ['developer'], 'commands': [], 'inputs': [], 'outputs': [], 'failure_modes': ([] if exists else ['missing_surface']), 'evidence_refs': [], 'roles': ['developer'], 'layer_status': {'technical':'observed'}, 'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['security','surface']})
        relations.append({'relation_id': stable_relation_id('securify', policy_id, 'applies_to' if False else 'governs', uid), 'from_id': policy_id, 'to_id': uid, 'relation_type': 'governs', 'owner_suite': 'securify', 'evidence_refs': [], 'confidence': 'moderate', 'created_at': now, 'last_verified': now})
    artifacts = [
        ('security_boundary_report.json','security-boundary-report', payload, [workflow_id, policy_id], 'deterministic-scan'),
        ('security_coverage.json','coverage-report', {'security_ok': payload.get('security_ok', False), 'risky_file_count': payload.get('risky_file_count',0), 'secret_hit_count': payload.get('secret_hit_count',0), 'next_steps': payload.get('next_steps',[])}, [workflow_id, policy_id], 'deterministic-scan'),
    ]
    graph = persist_simple_bundle(workspace=workspace, suite='securify', repo_root=repo_root, run_id=run_id, command='analyze', mode='security', lane='generate', units=units, relations=relations, extra_artifacts=artifacts, validation_summary={'unit_count': len(units), 'relation_count': len(relations), 'artifact_count': len(artifacts)+3, 'security_ok': payload.get('security_ok', False)}, residual_notes=['Security graph slice is bounded to repository hygiene rather than full application threat modeling.'])
    return graph | {'coverage': artifacts[1][2]}
