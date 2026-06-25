"""Canonical graph for mvpify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def persist_mvpify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist mvpify graph.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

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
    import_inventory = payload.get('import_inventory', {})
    plan = payload.get('plan', {})
    import_id = import_inventory.get('import_id', 'import')
    pkg_id = stable_unit_id('mvpify', 'import-package', import_id)
    workflow_id = stable_unit_id('mvpify', 'workflow', 'mvpify-import')
    units.append({
        'unit_id': pkg_id,
        'title': import_id,
        'entity_type': 'import-package',
        'owner_suite': 'mvpify',
        'source_paths': [import_inventory.get('normalized_root', '')],
        'summary': 'Imported MVP/package bundle.',
        'why_it_exists': 'Canonical representation of imported MVP material.',
        'contracts': [], 'dependencies': [], 'consumers': ['developer', 'operator'],
        'commands': ['import --mode mvp'], 'inputs': ['bundle'], 'outputs': ['import-manifest'],
        'failure_modes': [], 'evidence_refs': [], 'roles': ['developer', 'operator'],
        'layer_status': {'technical': 'observed'}, 'maturity': 'cross-linked', 'last_verified': now,
        'stability': 'observed', 'tags': ['mvp', 'import'],
    })
    units.append({
        'unit_id': workflow_id,
        'title': 'mvpify import',
        'entity_type': 'workflow',
        'owner_suite': 'mvpify',
        'source_paths': ['mvpify/adapter/service.py', 'mvpify/tools/importer.py'],
        'summary': 'Import workflow that normalizes and mirrors MVP/package material.',
        'why_it_exists': 'Primary graph-native intake workflow.',
        'contracts': [], 'dependencies': [], 'consumers': ['developer', 'operator'],
        'commands': ['import --mode mvp'], 'inputs': ['bundle'], 'outputs': ['import-manifest', 'documentation-bundle'],
        'failure_modes': [], 'evidence_refs': ['source:mvpify/tools/importer.py'], 'roles': ['developer', 'operator'],
        'layer_status': {'technical': 'observed'}, 'maturity': 'cross-linked', 'last_verified': now,
        'stability': 'observed', 'tags': ['mvp', 'workflow'],
    })
    relations.append({'relation_id': stable_relation_id('mvpify', workflow_id, 'imports', pkg_id), 'from_id': workflow_id, 'to_id': pkg_id, 'relation_type': 'imports', 'owner_suite': 'mvpify', 'evidence_refs': [], 'confidence': 'high', 'created_at': now, 'last_verified': now})

    # Process (class_name, count) one item at a time so persist_mvpify_graph applies the
    # same rule across the full collection.
    for class_name, count in sorted((import_inventory.get('preserved_class_counts') or {}).items()):
        class_unit_id = stable_unit_id('mvpify', 'artifact-type', f'import-class:{class_name}')
        units.append({
            'unit_id': class_unit_id,
            'title': class_name,
            'entity_type': 'artifact-type',
            'owner_suite': 'mvpify',
            'source_paths': [import_inventory.get('normalized_source_tree', '')],
            'summary': f'Preserved import material for class {class_name}.',
            'why_it_exists': 'Represents a materially preserved class of imported package content.',
            'contracts': [], 'dependencies': [], 'consumers': ['developer', 'operator', 'documentify'],
            'commands': [], 'inputs': [], 'outputs': [], 'failure_modes': [],
            'evidence_refs': [f"source:{p}" for p in (import_inventory.get('preserved_examples', {}) or {}).get(class_name, [])[:4]],
            'roles': ['developer', 'operator'], 'layer_status': {'technical': 'observed'}, 'maturity': 'evidence-fill',
            'last_verified': now, 'stability': 'observed', 'tags': ['mvp', 'preserved-class', class_name],
        })
        relations.append({'relation_id': stable_relation_id('mvpify', pkg_id, 'contains', class_unit_id), 'from_id': pkg_id, 'to_id': class_unit_id, 'relation_type': 'contains', 'owner_suite': 'mvpify', 'evidence_refs': [], 'confidence': 'high', 'created_at': now, 'last_verified': now})

    # Process sig one item at a time so persist_mvpify_graph applies the same rule
    # across the full collection.
    for sig in import_inventory.get('inventory', {}).get('suite_signals', [])[:12]:
        # Branch on not sig.get('present') so persist_mvpify_graph only continues along
        # the matching state path.
        if not sig.get('present'):
            continue
        uid = stable_unit_id('mvpify', 'suite', sig['name'])
        units.append({'unit_id': uid, 'title': sig['name'], 'entity_type': 'suite', 'owner_suite': 'mvpify', 'source_paths': sig.get('evidence', []), 'summary': 'Suite signal present in imported material.', 'why_it_exists': 'Represents suite presence in the imported package.', 'contracts': [], 'dependencies': [], 'consumers': ['developer'], 'commands': [], 'inputs': [], 'outputs': [], 'failure_modes': [], 'evidence_refs': [f"source:{e}" for e in sig.get('evidence', [])[:4]], 'roles': ['developer'], 'layer_status': {'technical': 'observed'}, 'maturity': 'evidence-fill', 'last_verified': now, 'stability': 'observed', 'tags': ['mvp', 'suite-signal']})
        relations.append({'relation_id': stable_relation_id('mvpify', pkg_id, 'contains', uid), 'from_id': pkg_id, 'to_id': uid, 'relation_type': 'contains', 'owner_suite': 'mvpify', 'evidence_refs': [], 'confidence': 'moderate', 'created_at': now, 'last_verified': now})

    manifest = {
        'import_id': import_id,
        'source': import_inventory.get('source', ''),
        'source_mode': import_inventory.get('source_mode', ''),
        'normalized_root': import_inventory.get('normalized_root', ''),
        'normalized_source_tree': import_inventory.get('normalized_source_tree', ''),
        'mirrored_docs_root': import_inventory.get('mirrored_docs_root', ''),
        'artifact_count': import_inventory.get('artifact_count', 0),
        'preserved_file_count': import_inventory.get('preserved_file_count', 0),
        'mirrored_file_count': import_inventory.get('mirrored_file_count', 0),
        'copied_doc_like_count': import_inventory.get('copied_doc_like_count', 0),
        'preserved_class_counts': import_inventory.get('preserved_class_counts', {}),
        'preserved_examples': import_inventory.get('preserved_examples', {}),
        'plan_step_count': len(plan.get('steps', [])),
        'highest_value_next_step': plan.get('highest_value_next_step', {}),
        'references_recorded': import_inventory.get('references_recorded', 0),
    }
    family_coverage = {
        'preserved_class_count': len(import_inventory.get('preserved_class_counts', {})),
        'preserved_class_counts': import_inventory.get('preserved_class_counts', {}),
        'preserved_file_count': import_inventory.get('preserved_file_count', 0),
        'mirrored_file_count': import_inventory.get('mirrored_file_count', 0),
    }
    artifacts = [
        ('import_manifest.json', 'import-manifest', manifest, [pkg_id, workflow_id], 'deterministic-scan'),
        ('import_family_coverage.json', 'coverage-report', family_coverage, [pkg_id, workflow_id], 'deterministic-scan'),
        ('import_drift_report.json', 'drift-report', {'suite_signal_count': len(import_inventory.get('inventory', {}).get('suite_signals', [])), 'plan_step_count': len(plan.get('steps', []))}, [pkg_id, workflow_id], 'derived'),
    ]
    return persist_simple_bundle(
        workspace=workspace,
        suite='mvpify',
        repo_root=repo_root,
        run_id=run_id,
        command='import',
        mode='mvp',
        lane='generate',
        units=units,
        relations=relations,
        extra_artifacts=artifacts,
        validation_summary={
            'unit_count': len(units),
            'relation_count': len(relations),
            'artifact_count': len(artifacts) + 3,
            'plan_step_count': len(plan.get('steps', [])),
            'preserved_file_count': import_inventory.get('preserved_file_count', 0),
        },
        residual_notes=['MVPify graph slice is bounded to imported package provenance, preservation, normalization, and handoff planning.'],
    ) | {'manifest_payload': manifest}
