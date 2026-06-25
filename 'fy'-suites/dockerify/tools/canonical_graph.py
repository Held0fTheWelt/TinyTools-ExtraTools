"""Canonical graph for dockerify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_dockerify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist dockerify graph.

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
    now = utc_now(); units=[]; relations=[]
    workflow_id = stable_unit_id('dockerify','workflow','dockerify-audit')
    units.append({'unit_id':workflow_id,'title':'dockerify audit','entity_type':'workflow','owner_suite':'dockerify','source_paths':['dockerify/adapter/service.py','dockerify/tools/docker_audit.py'],'summary':'Audit workflow for docker and compose governance surfaces.','why_it_exists':'Primary deployment topology governance workflow.','contracts':[],'dependencies':[],'consumers':['developer','operator'],'commands':['analyze --mode docker'],'inputs':['target_repo_root'],'outputs':['topology-map','drift-report'],'failure_modes':[],'evidence_refs':['source:dockerify/tools/docker_audit.py'],'roles':['developer','operator'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['docker','workflow']})
    # Process service one item at a time so persist_dockerify_graph applies the same
    # rule across the full collection.
    for service in payload.get('compose',{}).get('service_names',[])[:12]:
        uid = stable_unit_id('dockerify','deployment-surface',service)
        units.append({'unit_id':uid,'title':service,'entity_type':'deployment-surface','owner_suite':'dockerify','source_paths':['docker-compose.yml'],'summary':f'Compose deployment surface {service}.','why_it_exists':'Observed compose/runtime service surface.','contracts':[],'dependencies':[],'consumers':['developer','operator'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':['source:docker-compose.yml'],'roles':['developer','operator'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['docker','service']})
        relations.append({'relation_id':stable_relation_id('dockerify',workflow_id,'defines',uid),'from_id':workflow_id,'to_id':uid,'relation_type':'defines','owner_suite':'dockerify','evidence_refs':['source:docker-compose.yml'],'confidence':'high','created_at':now,'last_verified':now})
    coverage={'finding_count': len(payload.get('findings',[])), 'warning_count': len(payload.get('warnings',[])), 'required_service_count': payload.get('summary',{}).get('required_service_count',0), 'present_service_count': payload.get('summary',{}).get('present_service_count',0)}
    artifacts=[('topology_map.json','topology-map',payload,[workflow_id],'deterministic-scan'),('docker_drift_report.json','drift-report',coverage,[workflow_id],'deterministic-scan')]
    return persist_simple_bundle(workspace=workspace,suite='dockerify',repo_root=repo_root,run_id=run_id,command='analyze',mode='docker',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'finding_count':len(payload.get('findings',[]))},residual_notes=['Dockerify graph slice is bounded to deterministic repository docker/compose surfaces.']) | {'coverage': coverage}
