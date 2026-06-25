"""Canonical graph for despaghettify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_despag_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist despag graph.

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
    units=[]; relations=[]
    workflow_id = stable_unit_id('despaghettify','workflow','despaghettify-audit')
    units.append({'unit_id': workflow_id,'title':'despaghettify audit','entity_type':'workflow','owner_suite':'despaghettify','source_paths':['despaghettify/adapter/service.py'],'summary':'Audit workflow for structural complexity and refattening risks.','why_it_exists':'Primary structure-governance workflow.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':['analyze --mode structure'],'inputs':['target_repo_root'],'outputs':['drift-report','coverage-report'],'failure_modes':[],'evidence_refs':['source:despaghettify/adapter/service.py'],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['structure','workflow']})
    # Process concern one item at a time so persist_despag_graph applies the same rule
    # across the full collection.
    for concern in ['local_spike_guard','mixed_responsibility_guard','refattening_guard']:
        uid = stable_unit_id('despaghettify','policy-rule',concern)
        units.append({'unit_id':uid,'title':concern.replace('_',' '),'entity_type':'policy-rule','owner_suite':'despaghettify','source_paths':['despaghettify/adapter/service.py'],'summary':f'Policy guard {concern}.','why_it_exists':'Represents structural anti-spaghetti policy.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':['source:despaghettify/adapter/service.py'],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['structure','policy']})
        relations.append({'relation_id': stable_relation_id('despaghettify', workflow_id, 'governs', uid), 'from_id': workflow_id, 'to_id': uid, 'relation_type': 'governs', 'owner_suite': 'despaghettify', 'evidence_refs': [], 'confidence': 'high', 'created_at': now, 'last_verified': now})
    # Process hotspot one item at a time so persist_despag_graph applies the same rule
    # across the full collection.
    for hotspot in payload.get('ownership_hotspots', [])[:12]:
        uid = stable_unit_id('despaghettify','module', hotspot['path'])
        units.append({'unit_id':uid,'title':hotspot['path'].split('/')[-1],'entity_type':'module','owner_suite':'despaghettify','source_paths':[hotspot['path']],'summary':hotspot['issue'],'why_it_exists':'Observed structural hotspot.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[hotspot['issue']],'evidence_refs':[f"source:{hotspot['path']}"] ,'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['structure','hotspot']})
        relations.append({'relation_id': stable_relation_id('despaghettify', workflow_id, 'constrains', uid), 'from_id': workflow_id, 'to_id': uid, 'relation_type': 'constrains', 'owner_suite': 'despaghettify', 'evidence_refs': [f"source:{hotspot['path']}"], 'confidence': 'moderate', 'created_at': now, 'last_verified': now})
    coverage = {'global_category': payload.get('global_category'), 'local_spike_count': payload.get('local_spike_count',0), 'ownership_hotspot_count': len(payload.get('ownership_hotspots',[])), 'refattening_guard_report': payload.get('refattening_guard_report',{})}
    artifacts=[('structure_drift_report.json','drift-report',payload,[workflow_id],'deterministic-scan'),('structure_coverage.json','coverage-report',coverage,[workflow_id],'deterministic-scan')]
    return persist_simple_bundle(workspace=workspace,suite='despaghettify',repo_root=repo_root,run_id=run_id,command='analyze',mode='structure',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'local_spike_count':payload.get('local_spike_count',0)},residual_notes=['Structure graph slice is bounded to deterministic static complexity signals.']) | {'coverage': coverage}
