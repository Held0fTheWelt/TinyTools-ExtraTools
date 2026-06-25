"""Suite graph emit for fy_platform.evolution.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import target_repo_id, utc_now, workspace_root
from fy_platform.evolution.graph_store import CanonicalGraphStore, stable_artifact_id


def persist_simple_bundle(
    *,
    workspace: Path,
    suite: str,
    repo_root: Path,
    run_id: str,
    command: str,
    mode: str,
    lane: str,
    units: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    extra_artifacts: list[tuple[str, str, dict[str, Any], list[str], str]],
    validation_summary: dict[str, Any],
    residual_notes: list[str] | None = None,
    tool_chain: list[str] | None = None,
) -> dict[str, Any]:
    """Persist simple bundle.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        run_id: Identifier used to select an existing run or record.
        command: Named command for this operation.
        mode: Named mode for this operation.
        lane: Primary lane used by this step.
        units: Primary units used by this step.
        relations: Primary relations used by this step.
        extra_artifacts: Primary extra artifacts used by this step.
        validation_summary: Primary validation summary used by this
            step.
        residual_notes: Primary residual notes used by this step.
        tool_chain: Primary tool chain used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Build filesystem locations and shared state that the rest of persist_simple_bundle
    # reuses.
    workspace = workspace_root(workspace)
    now = utc_now()
    export_dir = workspace / suite / 'generated' / target_repo_id(repo_root) / run_id / 'evolution_graph'
    export_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    # Process (name, artifact_type, payload, source_units, ... one item at a time so
    # persist_simple_bundle applies the same rule across the full collection.
    for name, artifact_type, payload, source_units, evidence_mode in extra_artifacts:
        path = export_dir / name
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        artifacts.append(
            {
                'artifact_id': stable_artifact_id(suite, artifact_type, str(path.relative_to(workspace)), run_id),
                'artifact_type': artifact_type,
                'producer_suite': suite,
                'source_units': source_units,
                'source_artifacts': [],
                'run_id': run_id,
                'created_at': now,
                'source_revision': '',
                'maturity': 'evidence-fill',
                'evidence_mode': evidence_mode,
                'tracked_or_generated': 'generated',
                'render_family': 'json',
                'path': str(path.relative_to(workspace)),
                'status': 'complete',
            }
        )

    store = CanonicalGraphStore(workspace)
    graph = store.persist_bundle(
        suite=suite,
        run_id=run_id,
        command=command,
        mode=mode,
        lane=lane,
        target_repo_root=repo_root,
        units=units,
        relations=relations,
        artifacts=artifacts,
        validation_summary=validation_summary,
        residual_notes=residual_notes or [],
        tool_chain=tool_chain or ['fy_platform', suite],
    )

    all_unit_ids = [u['unit_id'] for u in units]
    existing_ids = [a['artifact_id'] for a in artifacts]
    core_specs = [
        ('unit-index', graph['written_paths']['unit_index'][1], all_unit_ids),
        ('relation-graph', graph['written_paths']['relation_graph'][1], all_unit_ids),
        ('run-manifest', graph['written_paths']['run_manifest'][1], []),
    ]
    # Process (artifact_type, relpath, src_units) one item at a time so
    # persist_simple_bundle applies the same rule across the full collection.
    for artifact_type, relpath, src_units in core_specs:
        artifacts.append(
            {
                'artifact_id': stable_artifact_id(suite, artifact_type, relpath, run_id),
                'artifact_type': artifact_type,
                'producer_suite': suite,
                'source_units': src_units,
                'source_artifacts': existing_ids.copy(),
                'run_id': run_id,
                'created_at': now,
                'source_revision': '',
                'maturity': 'cross-linked',
                'evidence_mode': 'deterministic-scan',
                'tracked_or_generated': 'generated',
                'render_family': 'json',
                'path': relpath,
                'status': 'complete',
            }
        )

    # Wire together the shared services that persist_simple_bundle depends on for the
    # rest of its workflow.
    artifact_index = {
        'schema_name': 'artifact.schema.json',
        'artifact_count': len(artifacts),
        'generated_at': now,
        'artifacts': artifacts,
    }
    graph['artifact_index'] = artifact_index
    # Process relpath one item at a time so persist_simple_bundle applies the same rule
    # across the full collection.
    for relpath in graph['written_paths']['artifact_index']:
        (workspace / relpath).write_text(json.dumps(artifact_index, indent=2) + '\n', encoding='utf-8')

    graph['run_manifest']['emitted_artifacts'] = [a['artifact_id'] for a in artifacts]
    # Process relpath one item at a time so persist_simple_bundle applies the same rule
    # across the full collection.
    for relpath in graph['written_paths']['run_manifest']:
        (workspace / relpath).write_text(json.dumps(graph['run_manifest'], indent=2) + '\n', encoding='utf-8')

    return graph | {'artifact_index': artifact_index}
