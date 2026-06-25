"""Canonical graph for metrify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_metrify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist metrify graph.

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
    workflow_id = stable_unit_id('metrify','workflow','metrify-report')
    units.append({'unit_id':workflow_id,'title':'metrify report','entity_type':'workflow','owner_suite':'metrify','source_paths':['metrify/adapter/service.py','metrify/tools/reporting.py'],'summary':'Reporting workflow for AI usage and cost metrics.','why_it_exists':'Primary cost and usage measurement workflow.','contracts':[],'dependencies':[],'consumers':['operator'],'commands':['metrics --mode report'],'inputs':['ledger'],'outputs':['cost-snapshot','acceptance-report'],'failure_modes':[],'evidence_refs':['source:metrify/tools/reporting.py'],'roles':['operator'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['metrics','workflow']})
    # Process row one item at a time so persist_metrify_graph applies the same rule
    # across the full collection.
    for row in payload.get('top_suites',[])[:8]:
        uid = stable_unit_id('metrify','suite',row['key'])
        units.append({'unit_id':uid,'title':row['key'],'entity_type':'suite','owner_suite':'metrify','source_paths':[],'summary':'Cost-observed suite.','why_it_exists':'Observed suite cost driver in the metrics ledger.','contracts':[],'dependencies':[],'consumers':['operator'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':[],'roles':['operator'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['metrics','suite']})
        relations.append({'relation_id':stable_relation_id('metrify',workflow_id,'summarizes',uid),'from_id':workflow_id,'to_id':uid,'relation_type':'summarizes','owner_suite':'metrify','evidence_refs':[],'confidence':'high','created_at':now,'last_verified':now})
    artifacts=[('cost_snapshot.json','cost-snapshot',payload,[workflow_id],'deterministic-scan')]
    return persist_simple_bundle(workspace=workspace,suite='metrify',repo_root=repo_root,run_id=run_id,command='metrics',mode='report',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'event_count':payload.get('event_count',0)},residual_notes=['Metrify graph slice is bounded to recorded AI usage and cost telemetry.'])
