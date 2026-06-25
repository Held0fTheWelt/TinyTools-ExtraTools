"""Evidence and governance section helpers for Documentify track output."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from documentify.tools.graph_inputs import ALL_GRAPH_SUITES, BROAD_SUITES
from documentify.tools.self_hosting_views import (
    contracts_markdown as _contracts_markdown,
    evidence_markdown as _self_hosting_evidence_markdown,
    self_hosting_health_markdown as _self_hosting_health_markdown,
    tracking_markdown as _tracking_markdown,
)

def _coverage_matrix_markdown(graph_inputs: dict[str, Any]) -> str:
    """Coverage matrix markdown.

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
    rows = ['| Evidence source | Units | Relations | Artifacts | Note |', '|---|---:|---:|---:|---|']
    notes = {
        'docify': 'code truth', 'contractify': 'normative', 'testify': 'proof', 'securify': 'security',
        'despaghettify': 'structure', 'dockerify': 'deployment', 'observifyfy': 'observability',
        'metrify': 'cost telemetry', 'templatify': 'template governance', 'usabilify': 'usability governance',
        'postmanify': 'api collection generation', 'mvpify': 'import provenance',
    }
    for suite in ALL_GRAPH_SUITES:
        ctx = graph_inputs[suite]
        if not ctx['available']:
            rows.append(f'| `{suite}` | 0 | 0 | 0 | unavailable |')
            continue
        rows.append(f"| `{suite}` | {ctx['unit_count']} | {ctx['relation_count']} | {ctx['artifact_count']} | {notes[suite]} |")
    return '# Coverage Matrix\n\n' + '\n'.join(rows) + '\n'

def _evidence_family_matrix_markdown(graph_inputs: dict[str, Any]) -> str:
    """Evidence family matrix markdown.

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
    rows = ['| Family | Contracts | Claims | Surfaces | Proofs | Linked claims | State |', '|---|---:|---:|---:|---:|---:|---|']
    if not graph_inputs['family_rows']:
        rows.append('| none | 0 | 0 | 0 | 0 | 0 | unavailable |')
    for row in graph_inputs['family_rows']:
        rows.append(f"| `{row['family']}` | {row['contract_count']} | {row['claim_count']} | {row['surface_count']} | {row['proof_count']} | {row['linked_claim_count']} | {row['state']} |")
    return '# Evidence Family Matrix\n\n' + '\n'.join(rows) + '\n'

def _governance_reference_markdown(graph_inputs: dict[str, Any]) -> str:
    """Governance reference markdown.

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
    lines = ['# Governance Reference', '']
    if not graph_inputs['family_rows']:
        lines.extend(['No family-aware shared graph input was available for this run.', ''])
        return '\n'.join(lines)
    lines.extend([f"Shared evidence mode: **{graph_inputs['shared_evidence_mode']}**.", '', '## Families', ''])
    family_breakdown = graph_inputs.get('contractify', {}).get('contract_map', {}).get('family_breakdown', {}) if graph_inputs.get('contractify', {}).get('available') else {}
    for row in graph_inputs['family_rows']:
        lines.extend([
            f"### {row['family']}",
            '',
            f"- contracts: {row['contract_count']}",
            f"- claims: {row['claim_count']}",
            f"- proofs: {row['proof_count']}",
            f"- linked claims: {row['linked_claim_count']}",
        ])
        meta = family_breakdown.get(row['family'], {})
        if meta.get('source_paths'):
            lines.append(f"- source paths: {', '.join(meta['source_paths'][:4])}")
        lines.append('')
    return '\n'.join(lines) + '\n'

def _evidence_gap_markdown(graph_inputs: dict[str, Any]) -> str:
    """Evidence gap markdown.

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
    gaps: list[str] = []
    for row in graph_inputs['family_rows']:
        if row['contract_count'] > 0 and row['linked_claim_count'] == 0:
            gaps.append(f"family `{row['family']}` has normative coverage but no persisted proof linkage yet")
        if row['proof_count'] > 0 and row['contract_count'] == 0:
            gaps.append(f"family `{row['family']}` has proof coverage but no normative contract family")
    if not gaps:
        gaps.append('no major family-level evidence gaps detected in the current graph-backed slice')
    return '# Evidence Gaps\n\n' + '\n'.join(f'- {g}' for g in gaps) + '\n'

def _evidence_status_markdown(graph_inputs: dict[str, Any]) -> str:
    """Evidence status markdown.

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
    linked_claim_count = sum(row['linked_claim_count'] for row in graph_inputs['family_rows'])
    linked_family_count = sum(1 for row in graph_inputs['family_rows'] if row['linked_claim_count'] > 0)
    lines = ['# Evidence Status', '', f"- shared_evidence_mode: `{graph_inputs['shared_evidence_mode']}`", f'- linked_claim_count: {linked_claim_count}', f'- linked_family_count: {linked_family_count}', '']
    for suite in ALL_GRAPH_SUITES:
        ctx = graph_inputs[suite]
        if ctx['available']:
            lines.append(f"- {suite}: run `{ctx['producer_run_id']}` / units={ctx['unit_count']} relations={ctx['relation_count']} artifacts={ctx['artifact_count']}")
        else:
            lines.append(f'- {suite}: unavailable')
    return '\n'.join(lines) + '\n'

def _stale_report_markdown(graph_inputs: dict[str, Any]) -> str:
    """Stale report markdown.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    family_lines = [f"- `{row['family']}` -> state={row['state']} linked_claims={row['linked_claim_count']}" for row in graph_inputs['family_rows']]
    if not family_lines:
        family_lines.append('- no family-level graph evidence available')
    return '# Stale Report\n\n' + f"- freshness_status: `{graph_inputs['shared_evidence_mode']}`\n\n## Family coverage\n\n" + '\n'.join(family_lines) + '\n'

def _broad_suite_participation_markdown(graph_inputs: dict[str, Any]) -> str:
    """Broad suite participation markdown.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    rows = ['| Suite | Available | Units | Relations | Artifacts | Focus |', '|---|---|---:|---:|---:|---|']
    focus = {
        'securify': 'security hygiene', 'despaghettify': 'structure governance', 'dockerify': 'deployment topology',
        'observifyfy': 'workspace observability', 'metrify': 'cost telemetry', 'templatify': 'template governance',
        'usabilify': 'usability governance', 'postmanify': 'api collection generation', 'mvpify': 'import provenance',
    }
    for suite in BROAD_SUITES:
        ctx = graph_inputs.get(suite, {'available': False})
        rows.append(f"| `{suite}` | {str(ctx.get('available', False)).lower()} | {ctx.get('unit_count', 0)} | {ctx.get('relation_count', 0)} | {ctx.get('artifact_count', 0)} | {focus[suite]} |")
    return '# Broad Suite Participation\n\n' + '\n'.join(rows) + '\n'

def _mvp_import_reference_markdown(graph_inputs: dict[str, Any]) -> str:
    """Mvp import reference markdown.

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
    lines = ['# MVP Import Reference', '']
    ctx = graph_inputs.get('mvpify', {})
    if not ctx.get('available'):
        lines.extend(['No graph-backed MVP import material is available for this run.', ''])
        return '\n'.join(lines)
    imp = ctx.get('import_manifest', {})
    lines.extend([
        f"- latest_import_id: `{imp.get('import_id', '')}`",
        f"- preserved_file_count: {imp.get('preserved_file_count', 0)}",
        f"- mirrored_file_count: {imp.get('mirrored_file_count', 0)}",
        f"- references_recorded: {imp.get('references_recorded', 0)}",
        f"- normalized_source_tree: `{imp.get('normalized_source_tree', '')}`",
        '',
        '## Preserved classes',
        '',
    ])
    class_counts = imp.get('preserved_class_counts', {}) or {}
    if not class_counts:
        lines.append('- none')
    else:
        for name, count in sorted(class_counts.items()):
            lines.append(f'- `{name}`: {count}')
    return '\n'.join(lines) + '\n'
