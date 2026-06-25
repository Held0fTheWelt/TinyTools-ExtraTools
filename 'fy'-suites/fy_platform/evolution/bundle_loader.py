"""Bundle loader for fy_platform.evolution.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.workspace import target_repo_id, workspace_root


def load_latest_suite_graph_bundle(root: Path | None, *, suite: str, target_repo_root: Path) -> dict[str, Any] | None:
    """Load latest suite graph bundle.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.
        target_repo_root: Root directory used to resolve
            repository-local paths.

    Returns:
        dict[str, Any] | None:
            Structured payload describing the outcome of the
            operation.
    """
    # Wire together the shared services that load_latest_suite_graph_bundle depends on
    # for the rest of its workflow.
    workspace = workspace_root(root)
    registry = EvidenceRegistry(workspace)
    tgt_id = target_repo_id(target_repo_root)
    # Process run one item at a time so load_latest_suite_graph_bundle applies the same
    # rule across the full collection.
    for run in registry.list_runs(suite):
        # Branch on run.get('target_repo_id') != tgt_id or run.ge... so
        # load_latest_suite_graph_bundle only continues along the matching state path.
        if run.get('target_repo_id') != tgt_id or run.get('status') != 'ok':
            continue
        # Build filesystem locations and shared state that the rest of
        # load_latest_suite_graph_bundle reuses.
        export_dir = workspace / suite / 'generated' / tgt_id / run['run_id'] / 'evolution_graph'
        # Branch on not export_dir.is_dir() so load_latest_suite_graph_bundle only
        # continues along the matching state path.
        if not export_dir.is_dir():
            continue
        out: dict[str, Any] = {'suite': suite, 'run_id': run['run_id'], 'target_repo_id': tgt_id, 'export_dir': str(export_dir.relative_to(workspace))}
        names = ('unit_index.json', 'relation_graph.json', 'artifact_index.json', 'run_manifest.json')
        ok = True
        # Process name one item at a time so load_latest_suite_graph_bundle applies the
        # same rule across the full collection.
        for name in names:
            path = export_dir / name
            # Branch on not path.is_file() so load_latest_suite_graph_bundle only
            # continues along the matching state path.
            if not path.is_file():
                ok = False
                break
            # Read and normalize the input data before load_latest_suite_graph_bundle
            # branches on or transforms it further.
            out[name] = json.loads(path.read_text(encoding='utf-8'))
        # Branch on ok so load_latest_suite_graph_bundle only continues along the
        # matching state path.
        if ok:
            return out
    return None


def load_bundle_artifact_payload(root: Path | None, bundle: dict[str, Any], artifact_type: str) -> dict[str, Any] | None:
    """Load bundle artifact payload.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        bundle: Primary bundle used by this step.
        artifact_type: Primary artifact type used by this step.

    Returns:
        dict[str, Any] | None:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    artifact_index = bundle.get('artifact_index.json', {})
    for artifact in artifact_index.get('artifacts', []):
        if artifact.get('artifact_type') != artifact_type:
            continue
        path = workspace / artifact['path']
        if path.is_file():
            return json.loads(path.read_text(encoding='utf-8'))
    return None
