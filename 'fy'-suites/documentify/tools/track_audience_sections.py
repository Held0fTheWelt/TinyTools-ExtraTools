"""Audience and bundle render helpers for Documentify track output."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from documentify.tools.document_builder import ROLE_MAP
from documentify.tools.graph_inputs import ALL_GRAPH_SUITES
from documentify.tools.self_hosting_views import build_tracking_context, self_hosting_ai_chunks
from fy_platform.ai.workspace import workspace_root

def _operations_and_risk_summary_markdown(graph_inputs: dict[str, Any]) -> str:
    """Operations and risk summary markdown.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = ['# Operations and Risk Summary', '']
    if graph_inputs.get('securify', {}).get('available'):
        sec = graph_inputs['securify'].get('security_report', {})
        lines.append(f"- security_ok: `{sec.get('security_ok', False)}`")
        lines.append(f"- risky_file_count: {sec.get('risky_file_count', 0)}")
    if graph_inputs.get('dockerify', {}).get('available'):
        topo = graph_inputs['dockerify'].get('topology_map', {})
        lines.append(f"- docker finding_count: {len(topo.get('findings', []))}")
    if graph_inputs.get('despaghettify', {}).get('available'):
        lines.append(f"- structure local_spike_count: {graph_inputs['despaghettify'].get('run_manifest', {}).get('validation_summary', {}).get('local_spike_count', 0)}")
    if graph_inputs.get('metrify', {}).get('available'):
        cost = graph_inputs['metrify'].get('cost_snapshot', {})
        lines.append(f"- total_cost_usd: {cost.get('total_cost_usd', 0.0)}")
    if graph_inputs.get('templatify', {}).get('available'):
        lines.append(f"- template_artifact_count: {graph_inputs['templatify'].get('artifact_count', 0)}")
    if graph_inputs.get('usabilify', {}).get('available'):
        acc = graph_inputs['usabilify'].get('acceptance_report', {})
        lines.append(f"- usability_area_count: {len(acc.get('areas', {}))}")
    if graph_inputs.get('postmanify', {}).get('available'):
        acc = graph_inputs['postmanify'].get('acceptance_report', {})
        lines.append(f"- postman_sub_suite_count: {acc.get('sub_suite_count', 0)}")
    if graph_inputs.get('mvpify', {}).get('available'):
        imp = graph_inputs['mvpify'].get('import_manifest', {})
        lines.append(f"- latest_import_id: `{imp.get('import_id', '')}`")
        lines.append(f"- preserved_file_count: {imp.get('preserved_file_count', 0)}")
        lines.append(f"- preserved_class_count: {len((imp.get('preserved_class_counts') or {}))}")
    return '\n'.join(lines) + '\n'

def _easy_doc(context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any], repo_root: Path) -> str:
    """Easy doc.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        context: Primary context used by this step.
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    services = ', '.join(context['services']) or 'no detected services'
    family_names = ', '.join(row['family'] for row in graph_inputs['family_rows'] if row['linked_claim_count'] > 0) or 'no linked families yet'
    self_hosting_note = ''
    if repo_root.resolve() == workspace_root(Path(__file__)).resolve():
        self_hosting_note = f"The fy-suites are self-hosting here, with {tracking['active_suite_count']} suites currently showing active tracking signals.\n\n"
    import_note = ''
    if graph_inputs.get('mvpify', {}).get('available'):
        imp = graph_inputs['mvpify'].get('import_manifest', {})
        import_note = f"Imported MVP material is available with **{imp.get('preserved_file_count', 0)} preserved files** across **{len((imp.get('preserved_class_counts') or {}))} preserved classes**.\n\n"
    return (
        '# Easy Overview\n\n'
        'This repository is worked on with the autark fy suites.\n\n'
        f'Visible service/package areas: **{services}**.\n\n'
        f"Shared evidence mode: **{graph_inputs['shared_evidence_mode']}**.\n\n"
        f'{self_hosting_note}'
        '## How this is governed\n\n'
        f'The current graph-backed slice is governed across these linked families: **{family_names}**.\n\n'
        f'{import_note}'
        '## Start points\n\n'
        '- Read the root README and docs/start-here first.\n'
        '- Use tests/run_tests.py to check the main Python test flow if present.\n'
        '- Use the generated role documents if you need a role-focused entry path.\n'
    )

def _technical_doc(context: dict[str, Any], graph_inputs: dict[str, Any]) -> str:
    """Technical doc.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        context: Primary context used by this step.
        graph_inputs: Primary graph inputs used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    service_lines = ''.join(f'- `{svc}/`\n' for svc in context['services']) or '- none\n'
    workflow_lines = ''.join(f'- `{wf}`\n' for wf in context['workflows']) or '- none\n'
    key_doc_lines = ''.join(f'- `{doc}`\n' for doc in context['key_docs']) or '- none\n'
    lines = [
        '# Technical Reference', '', '## Service surfaces', '', service_lines,
        '## Workflow surfaces', '', workflow_lines,
        '## Key docs', '', key_doc_lines,
        '## Shared evidence summary', '',
        f"- shared_evidence_mode: `{graph_inputs['shared_evidence_mode']}`",
        f"- linked_families: {sum(1 for row in graph_inputs['family_rows'] if row['linked_claim_count'] > 0)}",
        '',
    ]
    for suite in ALL_GRAPH_SUITES:
        ctx = graph_inputs[suite]
        if ctx['available']:
            lines.append(f"- {suite}: units={ctx['unit_count']} relations={ctx['relation_count']} artifacts={ctx['artifact_count']}")
        else:
            lines.append(f'- {suite}: unavailable')
    if graph_inputs['family_rows']:
        lines.extend(['', '## Linked evidence families', ''])
        for row in graph_inputs['family_rows']:
            lines.append(f"- `{row['family']}`: contracts={row['contract_count']} proofs={row['proof_count']} linked_claims={row['linked_claim_count']}")
    return '\n'.join(lines) + '\n'

def _role_doc(role: str, context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any], repo_root: Path) -> str:
    """Role doc.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        role: Primary role used by this step.
        context: Primary context used by this step.
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    info = ROLE_MAP[role]
    existing = [p for p in info['paths'] if (repo_root / p).exists()]
    shared_mode = graph_inputs['shared_evidence_mode']
    role_extra = ''
    if role == 'developer':
        role_extra = f"Tracking layers observed: {len(tracking['tracking_layers'])}. Active tracked suites: {tracking['active_suite_count']}.\n\n"
    elif role == 'operator':
        role_extra = f"Active tracked suites: {tracking['active_suite_count']}. Linked evidence families: {sum(1 for row in graph_inputs['family_rows'] if row['linked_claim_count'] > 0)}.\n\n"
    import_note = ''
    if graph_inputs.get('mvpify', {}).get('available'):
        import_note = f"Imported MVP preservation: {graph_inputs['mvpify'].get('import_manifest', {}).get('preserved_file_count', 0)} files / {len((graph_inputs['mvpify'].get('import_manifest', {}).get('preserved_class_counts') or {}))} classes.\n\n"
    return (
        f'# {role.capitalize()} Guide\n\n'
        f"{info['summary']}\n\n"
        f"Shared evidence mode: **{shared_mode}**.\n\n"
        f'{role_extra}'
        f'{import_note}'
        '## Relevant paths\n\n' + ''.join(f'- `{p}`\n' for p in existing)
    )

def _docs_site_blueprint(context: dict[str, Any]) -> str:
    """Docs site blueprint.

    Args:
        context: Primary context used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    services = ', '.join(context['services']) or 'none'
    docs_dirs = ', '.join(context['docs_dirs']) or 'none'
    workflows = ', '.join(context['workflows']) or 'none'
    return (
        '# Documentation Site Blueprint\n\n'
        'Recommended site model for the fy suites and exported outward docs.\n\n'
        '## Recommended structure\n\n'
        '- One main docs site can use multiple sidebars for easy, technical, role, and AI tracks.\n'
        '- If some documentation families later need different version histories or release lifecycles, move those families to distinct docs plugin instances.\n'
        '- Keep AI-readable bundles generated from the same source tree so search and export stay aligned.\n\n'
        '## Suggested sidebars\n\n'
        '- easy\n- technical\n- role-admin\n- role-developer\n- role-operator\n- role-writer\n- ai-read\n\n'
        '## Current repository signals\n\n'
        f'- services: {services}\n'
        f'- docs dirs: {docs_dirs}\n'
        f'- workflows: {workflows}\n'
    )

def _status_page(context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> str:
    """Status page.

    Args:
        context: Primary context used by this step.
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    services = ', '.join(context['services']) or 'no clear services found'
    docs_dirs = ', '.join(context['docs_dirs']) or 'no docs directories found'
    workflows = ', '.join(context['workflows']) or 'no workflows found'
    return (
        '# Documentation Status — Most-Recent-Next-Steps\n\n'
        'This page uses simple language.\n\n'
        '## What was found\n\n'
        f'- services: {services}\n'
        f'- docs directories: {docs_dirs}\n'
        f'- workflows: {workflows}\n'
        f"- graph status: {graph_inputs['shared_evidence_mode']}\n"
        f"- active tracked suites: {tracking['active_suite_count']}\n\n"
        '## Most-Recent-Next-Steps\n\n'
        '- Read the easy overview first if you are new to this repository.\n'
        '- Use the technical reference when you need exact paths and system surfaces.\n'
        '- Open the role guide that matches your current job.\n'
        '- Use the AI-read bundle when another suite needs searchable structured context.\n'
        '- Build one main docs site with separate sidebars first. Only split into multiple docs instances when different version histories are really needed.\n'
    )

def _ai_read_bundle(context: dict[str, Any], repo_root: Path, graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> dict[str, Any]:
    """Ai read bundle.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        context: Primary context used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        graph_inputs: Primary graph inputs used by this step.
        tracking: Primary tracking used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    aliases = {
        'repo': [repo_root.name, 'target-repo'],
        'tests': ['testing', 'verification', 'pytest'],
        'docs': ['documentation', 'manuals'],
        'graph': ['canonical units', 'relations', 'code graph', 'shared evidence'],
    }
    chunks = [
        {'id': 'services', 'title': 'Services', 'text': ', '.join(context['services'])},
        {'id': 'docs_dirs', 'title': 'Documentation dirs', 'text': ', '.join(context['docs_dirs'])},
        {'id': 'workflows', 'title': 'CI workflows', 'text': ', '.join(context['workflows'])},
        {'id': 'canonical_graph', 'title': 'Governed shared evidence', 'text': f"Mode {graph_inputs['shared_evidence_mode']} with {len(graph_inputs['family_rows'])} evidence families."},
        {'id': 'normative_graph', 'title': 'Normative graph', 'text': f"Contractify available={graph_inputs.get('contractify', {}).get('available', False)} units={graph_inputs.get('contractify', {}).get('unit_count', 0)}."},
        {'id': 'proof_graph', 'title': 'Proof graph', 'text': f"Testify available={graph_inputs.get('testify', {}).get('available', False)} units={graph_inputs.get('testify', {}).get('unit_count', 0)}."},
        {'id': 'evidence_families', 'title': 'Evidence families', 'text': ', '.join(row['family'] for row in graph_inputs['family_rows']) or 'none'},
    ]
    if graph_inputs.get('mvpify', {}).get('available'):
        imp = graph_inputs['mvpify'].get('import_manifest', {})
        chunks.append({'id': 'mvp_import', 'title': 'Imported MVP material', 'text': f"Latest import {imp.get('import_id', '')} preserved {imp.get('preserved_file_count', 0)} files across {len((imp.get('preserved_class_counts') or {}))} classes."})
        chunks.append({'id': 'mvp_import_classes', 'title': 'Imported MVP classes', 'text': ', '.join(sorted((imp.get('preserved_class_counts') or {}).keys())) or 'none'})
    chunks.extend(self_hosting_ai_chunks(graph_inputs, tracking))
    return {'aliases': aliases, 'chunks': chunks, 'context': context, 'graph_inputs': graph_inputs, 'tracking': tracking}
