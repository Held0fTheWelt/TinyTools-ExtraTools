"""Self hosting views for documentify.tools.

"""
from __future__ import annotations

"""Markdown and AI-bundle helpers for the fy-suites self-hosting pass."""

from pathlib import Path
from typing import Any

from fy_platform.ai.self_hosting_tracking import build_self_hosting_tracking_snapshot


def build_tracking_context(repo_root: Path) -> dict[str, Any]:
    """Return the current self-hosting tracking snapshot for the repo root.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return build_self_hosting_tracking_snapshot(repo_root)


def tracking_markdown(tracking: dict[str, Any]) -> str:
    """Tracking markdown.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        tracking: Primary tracking used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    rows = ['| Suite | Runs | Graph runs | Journals | Binding | Generated targets |', '|---|---:|---:|---:|---|---:|']
    # Process row one item at a time so tracking_markdown applies the same rule across
    # the full collection.
    for row in tracking['suite_rows']:
        rows.append(
            f"| `{row['suite']}` | {row['run_count']} | {row['graph_run_count']} | {row['journal_count']} | "
            f"{'yes' if row['binding_present'] else 'no'} | {row['generated_target_count']} |"
        )
    layer_lines = [
        f"- `{name}` → `{meta['path']}` (exists={meta['exists']}, files={meta['file_count']}, latest=`{meta['latest_child']}`)"
        for name, meta in tracking['tracking_layers'].items()
    ]
    blind_spots = tracking['blind_spots'] or ['no major tracking blind spots detected']
    return (
        '# Self-Hosting Tracking\n\n'
        f"{tracking['summary']}\n\n"
        '## Tracking layers\n\n' + '\n'.join(layer_lines) + '\n\n'
        '## Suite activity\n\n' + '\n'.join(rows) + '\n\n'
        '## Blind spots\n\n' + '\n'.join(f'- {item}' for item in blind_spots) + '\n'
    )


def contracts_markdown(graph_inputs: dict[str, Any]) -> str:
    """Contracts markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    contractify = graph_inputs.get('contractify', {})
    if not contractify.get('available'):
        return '# Self-Hosting Contracts\n\nNo Contractify graph input was available for this run.\n'
    inventory = contractify.get('normative_inventory', {})
    family_counts = inventory.get('family_counts', {})
    lines = ['# Self-Hosting Contracts', '', f"Shared evidence mode: **{graph_inputs['shared_evidence_mode']}**.", '', '## Contract families', '']
    if not family_counts:
        lines.append('- No family-aware contract coverage was emitted.')
        return '\n'.join(lines) + '\n'
    for family, meta in sorted(family_counts.items()):
        lines.extend([
            f"### {family}",
            '',
            f"- contracts: {meta.get('contract_count', 0)}",
            f"- claims: {meta.get('claim_count', 0)}",
            f"- surfaces: {meta.get('surface_count', 0)}",
            '',
        ])
    return '\n'.join(lines) + '\n'


def evidence_markdown(graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> str:
    """Evidence markdown.

    Args:
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    family_rows = graph_inputs.get('family_rows', [])
    linked = sum(row['linked_claim_count'] for row in family_rows)
    broad_active = [suite for suite in ('securify', 'despaghettify', 'dockerify', 'observifyfy', 'metrify', 'templatify', 'usabilify', 'postmanify', 'mvpify') if graph_inputs.get(suite, {}).get('available')]
    return (
        '# Self-Hosting Evidence\n\n'
        f"- shared_evidence_mode: `{graph_inputs['shared_evidence_mode']}`\n"
        f"- linked_claim_count: {linked}\n"
        f"- tracked_suite_count: {tracking['tracked_suite_count']}\n"
        f"- active_suite_count: {tracking['active_suite_count']}\n"
        f"- broad_suite_inputs: {', '.join(broad_active) if broad_active else 'none'}\n"
    )


def self_hosting_health_markdown(graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> str:
    """Self hosting health markdown.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    blind_spots = tracking['blind_spots'] or ['no major tracking blind spots detected']
    missing_suites = [suite for suite, ctx in graph_inputs.items() if isinstance(ctx, dict) and suite not in {'family_rows', 'shared_evidence_mode'} and not ctx.get('available', False)]
    lines = [
        '# Self-Hosting Health',
        '',
        f"- graph_mode: `{graph_inputs['shared_evidence_mode']}`",
        f"- tracked_suite_count: {tracking['tracked_suite_count']}",
        f"- active_suite_count: {tracking['active_suite_count']}",
        '',
        '## Blind spots',
        '',
    ]
    lines.extend(f'- {item}' for item in blind_spots)
    lines.extend(['', '## Missing graph inputs in this run', ''])
    if missing_suites:
        lines.extend(f'- {suite}' for suite in sorted(missing_suites))
    else:
        lines.append('- none')
    return '\n'.join(lines) + '\n'


def self_hosting_ai_chunks(graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> list[dict[str, str]]:
    """Return AI-read chunks that summarize the self-hosting posture.

    Args:
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.

    Returns:
        list[dict[str, str]]:
            Structured payload describing the outcome of the
            operation.
    """
    active_suites = [row['suite'] for row in tracking['suite_rows'] if row['graph_run_count'] > 0]
    return [
        {'id': 'self_hosting_tracking', 'title': 'Self-hosting tracking', 'text': tracking['summary']},
        {'id': 'self_hosting_contracts', 'title': 'Self-hosting contracts', 'text': ', '.join(sorted((graph_inputs.get('contractify', {}).get('normative_inventory', {}) or {}).get('family_counts', {}).keys())) or 'none'},
        {'id': 'self_hosting_active_suites', 'title': 'Self-hosting active suites', 'text': ', '.join(active_suites) if active_suites else 'none'},
    ]
