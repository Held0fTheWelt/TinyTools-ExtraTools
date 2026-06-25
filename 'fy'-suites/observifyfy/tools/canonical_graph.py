"""Canonical graph for observifyfy.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_observifyfy_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist observifyfy graph.

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
    workflow_id = stable_unit_id('observifyfy','workflow','observifyfy-audit')
    units.append({'unit_id':workflow_id,'title':'observifyfy audit','entity_type':'workflow','owner_suite':'observifyfy','source_paths':['observifyfy/adapter/service.py','observifyfy/tools/hub_cli.py'],'summary':'Audit workflow for cross-suite inventory and next-step observability.','why_it_exists':'Primary observability and internal tracking workflow.','contracts':[],'dependencies':[],'consumers':['operator'],'commands':['analyze --mode observability'],'inputs':['target_repo_root'],'outputs':['acceptance-report','ai-context-pack'],'failure_modes':[],'evidence_refs':['source:observifyfy/tools/hub_cli.py'],'roles':['operator'],'layer_status':{'technical':'observed'},'maturity':'cross-linked','last_verified':now,'stability':'observed','tags':['observability','workflow']})
    inventory = payload.get('inventory',{})
    # Process suite one item at a time so persist_observifyfy_graph applies the same
    # rule across the full collection.
    for suite in [s for s in inventory.get('suites',[]) if s.get('exists')][:12]:
        uid = stable_unit_id('observifyfy','suite',suite['name'])
        units.append({'unit_id':uid,'title':suite['name'],'entity_type':'suite','owner_suite':'observifyfy','source_paths':[],'summary':'Tracked suite in observifyfy inventory.','why_it_exists':'Observed suite participation inventory row.','contracts':[],'dependencies':[],'consumers':['operator'],'commands':[],'inputs':[],'outputs':[],'failure_modes':[],'evidence_refs':[],'roles':['operator'],'layer_status':{'technical':'observed'},'maturity':'evidence-fill','last_verified':now,'stability':'observed','tags':['observability','suite']})
        relations.append({'relation_id':stable_relation_id('observifyfy',workflow_id,'summarizes',uid),'from_id':workflow_id,'to_id':uid,'relation_type':'summarizes','owner_suite':'observifyfy','evidence_refs':[],'confidence':'moderate','created_at':now,'last_verified':now})
    acceptance={'existing_suite_count': inventory.get('existing_suite_count',0), 'suite_count': inventory.get('suite_count',0), 'highest_value_next_step': (payload.get('next_steps',{}).get('highest_value_next_step') or {})}
    artifacts=[('observability_acceptance.json','acceptance-report',payload,[workflow_id],'deterministic-scan'),('observability_ai_pack.json','ai-context-pack',payload.get('ai_context',{}),[workflow_id],'derived')]
    return persist_simple_bundle(workspace=workspace,suite='observifyfy',repo_root=repo_root,run_id=run_id,command='analyze',mode='observability',lane='generate',units=units,relations=relations,extra_artifacts=artifacts,validation_summary={'unit_count':len(units),'relation_count':len(relations),'artifact_count':len(artifacts)+3,'tracked_suites':inventory.get('existing_suite_count',0)},residual_notes=['Observifyfy graph slice is bounded to workspace inventory and next-step observability.']) | {'acceptance': acceptance}
