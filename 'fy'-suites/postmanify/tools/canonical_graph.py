"""Canonical graph for postmanify.tools.

"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle

def persist_postmanify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist postmanify graph.

    Control flow branches on the parsed state rather than relying on one
    linear path.

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
    workflow_id=stable_unit_id('postmanify','workflow','postmanify-audit')
    units.append({'unit_id':workflow_id,'title':'postmanify audit','entity_type':'workflow','owner_suite':'postmanify','source_paths':['postmanify/adapter/service.py','postmanify/tools/openapi_postman.py'],'summary':'Audit/generation workflow for OpenAPI-derived Postman collections.','why_it_exists':'Primary API collection generation workflow.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':['analyze --mode api'],'inputs':['target_repo_root'],'outputs':['documentation-bundle','acceptance-report'],'failure_modes':[],'evidence_refs':['source:postmanify/tools/openapi_postman.py'],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['api','workflow']})
    # Build filesystem locations and shared state that the rest of
    # persist_postmanify_graph reuses.
    master_path=payload.get('master_path','')
    # Branch on master_path so persist_postmanify_graph only continues along the
    # matching state path.
    if master_path:
        uid=stable_unit_id('postmanify','artifact-type','postman-master-collection')
        units.append({'unit_id':uid,'title':'master_collection','entity_type':'artifact-type','owner_suite':'postmanify','source_paths':[master_path],'summary':'Master Postman collection derived from OpenAPI.','why_it_exists':'Represents the generated API collection surface.','contracts':[],'dependencies':[],'consumers':['developer'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':[f"source:{master_path}"],'roles':['developer'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['api','collection']})
        relations.append({'relation_id':stable_relation_id('postmanify',workflow_id,'produces',uid),'from_id':workflow_id,'to_id':uid,'relation_type':'produces','owner_suite':'postmanify','evidence_refs':[f"source:{master_path}"],'confidence':'high','created_at':now,'last_verified':now})
    artifacts=[('postman_bundle.json','documentation-bundle',payload,[workflow_id],'deterministic-scan'),('postman_acceptance.json','acceptance-report',{'sub_suite_count': payload.get('sub_suite_count',0), 'master_path': payload.get('master_path','')},[workflow_id],'deterministic-scan')]
    return persist_simple_bundle(workspace=workspace,suite='postmanify',repo_root=repo_root,run_id=run_id,command='analyze',mode='api',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'sub_suite_count':payload.get('sub_suite_count',0)},residual_notes=['Postmanify graph slice is bounded to OpenAPI-derived collection generation.'])
