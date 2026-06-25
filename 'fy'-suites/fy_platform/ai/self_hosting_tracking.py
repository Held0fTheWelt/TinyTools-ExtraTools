"""Self hosting tracking for fy_platform.ai.

"""
from __future__ import annotations

"""Helpers for summarizing the fy-suites' own internal tracking layers.

The self-hosting pass needs a repository-local picture of how the suites track
runs, graph bundles, journals, metrics, bindings, backups, and registry state.
This module gathers that picture from the real workspace so documentation and
status views can stay grounded in current repository truth rather than static
claims.
"""

from pathlib import Path
from typing import Any

from fy_platform.ai.evolution_contract_pack import suite_names_for_ownership
from fy_platform.ai.workspace import workspace_root

TRACKING_LAYERS = {
    'runs': '.fydata/runs',
    'graph_runs': '.fydata/evolution_graph/runs',
    'journal': '.fydata/journal',
    'metrics': '.fydata/metrics',
    'bindings': '.fydata/bindings',
    'registry': '.fydata/registry',
    'backups': '.fydata/backups',
    'semantic_index': '.fydata/index',
}


def _count_files(path: Path) -> int:
    """Count files.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    return sum(1 for item in path.rglob('*') if item.is_file()) if path.is_dir() else 0


def _latest_named_child(path: Path) -> str:
    """Latest named child.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    # Branch on not path.is_dir() so _latest_named_child only continues along the
    # matching state path.
    if not path.is_dir():
        return ''
    children = sorted((item.name for item in path.iterdir()), reverse=True)
    return children[0] if children else ''


def build_self_hosting_tracking_snapshot(root: Path | None = None) -> dict[str, Any]:
    """Return an evidence-backed summary of the fy-suites tracking layers.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """

    workspace = workspace_root(root)
    suite_names = suite_names_for_ownership(workspace)

    tracking_layers: dict[str, dict[str, Any]] = {}
    for name, rel in TRACKING_LAYERS.items():
        path = workspace / rel
        tracking_layers[name] = {
            'path': rel,
            'exists': path.exists(),
            'file_count': _count_files(path),
            'latest_child': _latest_named_child(path),
        }

    suite_rows: list[dict[str, Any]] = []
    active_suite_count = 0
    graph_root = workspace / '.fydata' / 'evolution_graph' / 'runs'
    for suite in suite_names:
        runs_dir = workspace / '.fydata' / 'runs' / suite
        journal_dir = workspace / '.fydata' / 'journal' / suite
        binding_file = workspace / '.fydata' / 'bindings' / f'{suite}.json'
        graph_run_names = sorted(graph_root.glob(f'{suite}-*')) if graph_root.is_dir() else []
        generated_root = workspace / suite / 'generated'
        generated_target_count = sum(1 for item in generated_root.iterdir() if item.is_dir()) if generated_root.is_dir() else 0
        row = {
            'suite': suite,
            'run_count': sum(1 for item in runs_dir.iterdir() if item.is_file()) if runs_dir.is_dir() else 0,
            'latest_run_record': _latest_named_child(runs_dir),
            'journal_count': len(list(journal_dir.glob('*.jsonl'))) if journal_dir.is_dir() else 0,
            'graph_run_count': len(graph_run_names),
            'latest_graph_run': graph_run_names[-1].name if graph_run_names else '',
            'binding_present': binding_file.is_file(),
            'generated_target_count': generated_target_count,
        }
        if any([
            row['run_count'],
            row['journal_count'],
            row['graph_run_count'],
            row['binding_present'],
            row['generated_target_count'],
        ]):
            active_suite_count += 1
        suite_rows.append(row)

    blind_spots: list[str] = []
    if not tracking_layers['registry']['exists']:
        blind_spots.append('registry layer missing')
    if not tracking_layers['semantic_index']['exists']:
        blind_spots.append('semantic index layer missing')
    inactive = [row['suite'] for row in suite_rows if row['suite'] not in {'fy_platform', 'brokenify'} and row['graph_run_count'] == 0 and row['run_count'] == 0 and row['journal_count'] == 0 and not row['binding_present'] and row['generated_target_count'] == 0]
    if inactive:
        blind_spots.append('suites with no visible run or graph activity: ' + ', '.join(inactive))

    return {
        'workspace_root': str(workspace),
        'tracking_layers': tracking_layers,
        'suite_rows': suite_rows,
        'active_suite_count': active_suite_count,
        'tracked_suite_count': len(suite_rows),
        'blind_spots': blind_spots,
        'summary': f'Self-hosting tracking sees {active_suite_count} active suites across {len(tracking_layers)} tracking layers.',
    }
