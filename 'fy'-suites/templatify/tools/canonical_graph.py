"""Canonical graph for templatify.tools.

"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle

def persist_templatify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist templatify graph.

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
    now=utc_now(); units=[]; relations=[]
    workflow_id=stable_unit_id('templatify','workflow','templatify-audit')
    units.append({'unit_id':workflow_id,'title':'templatify audit','entity_type':'workflow','owner_suite':'templatify','source_paths':['templatify/adapter/service.py'],'summary':'Audit workflow for template registry, validation, and preview drift.','why_it_exists':'Primary template-governance workflow.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':['analyze --mode templates'],'inputs':['target_repo_root'],'outputs':['documentation-bundle','drift-report'],'failure_modes':[],'evidence_refs':['source:templatify/adapter/service.py'],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['templates','workflow']})
    # Process item one item at a time so persist_templatify_graph applies the same rule
    # across the full collection.
    for item in payload.get('templates',[])[:12]:
        uid=stable_unit_id('templatify','artifact-type',item['template_id'])
        units.append({'unit_id':uid,'title':item['template_id'],'entity_type':'artifact-type','owner_suite':'templatify','source_paths':[item['path']],'summary':'Registered template artifact.','why_it_exists':'Observed render-family template registry record.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':[f"source:{item['path']}"],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['templates','artifact-type']})
        relations.append({'relation_id':stable_relation_id('templatify',workflow_id,'defines',uid),'from_id':workflow_id,'to_id':uid,'relation_type':'defines','owner_suite':'templatify','evidence_refs':[f"source:{item['path']}"],'confidence':'high','created_at':now,'last_verified':now})
    artifacts=[('template_documentation_bundle.json','documentation-bundle',payload,[workflow_id],'deterministic-scan'),('template_drift_report.json','drift-report',payload.get('drift',{}),[workflow_id],'deterministic-scan')]
    return persist_simple_bundle(workspace=workspace,suite='templatify',repo_root=repo_root,run_id=run_id,command='analyze',mode='templates',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'template_count':len(payload.get('templates',[]))},residual_notes=['Templatify graph slice is bounded to template registry and drift surfaces.'])
