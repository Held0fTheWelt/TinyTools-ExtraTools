"""Graph inputs for documentify.tools.

"""
from __future__ import annotations

"""Graph-input loading helpers for Documentify.

This module keeps the graph-loading and family-state logic separate from the
markdown/view compilation layer so the document compiler is easier to reason
about and extend.
"""

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import workspace_root
from fy_platform.evolution.bundle_loader import load_bundle_artifact_payload, load_latest_suite_graph_bundle

PRIMARY_SUITES = ('docify', 'contractify', 'testify')
BROAD_SUITES = ('securify', 'despaghettify', 'dockerify', 'observifyfy', 'metrify', 'templatify', 'usabilify', 'postmanify', 'mvpify')
ALL_GRAPH_SUITES = PRIMARY_SUITES + BROAD_SUITES


def build_family_rows(graph_inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Merge normative/proof family state into stable row records.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    contract_families = graph_inputs.get('contractify', {}).get('normative_inventory', {}).get('family_counts', {}) if graph_inputs.get('contractify', {}).get('available') else {}
    proof_counts = graph_inputs.get('testify', {}).get('claim_proof_status', {}).get('proof_family_counts', {}) if graph_inputs.get('testify', {}).get('available') else {}
    linked_counts = graph_inputs.get('testify', {}).get('claim_proof_status', {}).get('linked_claims_by_family', {}) if graph_inputs.get('testify', {}).get('available') else {}
    rows: list[dict[str, Any]] = []
    # Process family one item at a time so build_family_rows applies the same rule
    # across the full collection.
    for family in sorted(set(contract_families) | set(proof_counts) | set(linked_counts)):
        cmeta = contract_families.get(family, {})
        pcount = proof_counts.get(family, 0)
        lcount = linked_counts.get(family, 0)
        state = 'linked' if lcount > 0 else 'normative-only' if cmeta else 'proof-only'
        rows.append({
            'family': family,
            'contract_count': cmeta.get('contract_count', 0),
            'claim_count': cmeta.get('claim_count', 0),
            'surface_count': cmeta.get('surface_count', 0),
            'proof_count': pcount,
            'linked_claim_count': lcount,
            'state': state,
        })
    return rows


def shared_evidence_mode(graph_inputs: dict[str, Any], family_rows: list[dict[str, Any]]) -> str:
    """Collapse the visible graph state into one conservative mode label.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        graph_inputs: Primary graph inputs used by this step.
        family_rows: Primary family rows used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    doc = graph_inputs.get('docify', {}).get('available', False)
    contract = graph_inputs.get('contractify', {}).get('available', False)
    proof = graph_inputs.get('testify', {}).get('available', False)
    mode = 'code-truth-only'
    if doc:
        mode = 'code-truth'
    if contract:
        mode = 'normative-backed'
    if contract and proof:
        mode = 'proof-backed'
    if doc and contract and proof:
        mode = 'governed-shared-evidence'
    if doc and contract and proof and sum(1 for row in family_rows if row['linked_claim_count'] > 0) >= 2:
        mode = 'multi-family-governed-shared-evidence'
    return mode


def _artifact_payload_for_suite(workspace: Path, bundle: dict[str, Any], suite: str) -> dict[str, Any]:
    """Artifact payload for suite.

    Args:
        workspace: Primary workspace used by this step.
        bundle: Primary bundle used by this step.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    mapping = {
        'contractify': {'normative_inventory': 'normative-inventory', 'contract_map': 'contract-map'},
        'testify': {'proof_report': 'proof-report', 'claim_proof_status': 'claim-proof-status'},
        'securify': {'security_report': 'security-boundary-report'},
        'dockerify': {'topology_map': 'topology-map'},
        'observifyfy': {'acceptance_report': 'acceptance-report'},
        'metrify': {'cost_snapshot': 'cost-snapshot'},
        'templatify': {'documentation_bundle': 'documentation-bundle'},
        'usabilify': {'acceptance_report': 'acceptance-report'},
        'postmanify': {'acceptance_report': 'acceptance-report'},
        'mvpify': {'import_manifest': 'import-manifest'},
        'despaghettify': {'structure_report': 'drift-report'},
        'docify': {'coverage_report': 'coverage-report'},
    }
    return {key: load_bundle_artifact_payload(workspace, bundle, artifact_type) or {} for key, artifact_type in mapping.get(suite, {}).items()}


def build_suite_graph_context(repo_root: Path) -> dict[str, Any]:
    """Load the latest graph-backed evidence inputs for Documentify.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(Path(__file__))
    graph_inputs: dict[str, Any] = {}
    for suite in ALL_GRAPH_SUITES:
        bundle = load_latest_suite_graph_bundle(workspace, suite=suite, target_repo_root=repo_root)
        if not bundle:
            graph_inputs[suite] = {'available': False}
            continue
        unit_index = bundle['unit_index.json']
        relation_graph = bundle['relation_graph.json']
        artifact_index = bundle['artifact_index.json']
        run_manifest = bundle['run_manifest.json']
        entity_counts: dict[str, int] = {}
        for unit in unit_index.get('units', []):
            entity_counts[unit['entity_type']] = entity_counts.get(unit['entity_type'], 0) + 1
        ctx = {
            'available': True,
            'producer_suite': suite,
            'producer_run_id': bundle['run_id'],
            'unit_count': len(unit_index.get('units', [])),
            'relation_count': len(relation_graph.get('relations', [])),
            'artifact_count': len(artifact_index.get('artifacts', [])),
            'entity_counts': entity_counts,
            'run_manifest': run_manifest,
            'bundle': bundle,
            'export_dir': bundle['export_dir'],
        }
        ctx.update(_artifact_payload_for_suite(workspace, bundle, suite))
        graph_inputs[suite] = ctx
    family_rows = build_family_rows(graph_inputs)
    graph_inputs['family_rows'] = family_rows
    graph_inputs['shared_evidence_mode'] = shared_evidence_mode(graph_inputs, family_rows)
    return graph_inputs
