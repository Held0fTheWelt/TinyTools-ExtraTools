"""Workspace status site for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.policy.suite_quality_policy import CORE_SUITES, OPTIONAL_SUITES
from fy_platform.ai.workspace import write_json, write_text, workspace_root, write_platform_doc_artifacts


def _status_path(workspace: Path, suite: str) -> Path:
    """Status path.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace / suite / 'reports' / 'status' / 'most_recent_next_steps.json'


def build_workspace_status_site(workspace: Path, suites: list[str] | None = None) -> dict[str, Any]:
    """Build workspace status site.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace: Primary workspace used by this step.
        suites: Primary suites used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(workspace)
    # Branch on suites is None so build_workspace_status_site only continues along the
    # matching state path.
    if suites is None:
        suites = sorted({*CORE_SUITES, *OPTIONAL_SUITES, *[p.name for p in workspace.iterdir() if p.is_dir() and (p / 'adapter').is_dir()]})
    rows = []
    # Process suite one item at a time so build_workspace_status_site applies the same
    # rule across the full collection.
    for suite in suites:
        # Build filesystem locations and shared state that the rest of
        # build_workspace_status_site reuses.
        status_path = _status_path(workspace, suite)
        # Branch on not status_path.is_file() so build_workspace_status_site only
        # continues along the matching state path.
        if not status_path.is_file():
            rows.append({'suite': suite, 'has_status': False, 'ok': False, 'summary': 'No status page generated yet.', 'next_steps': ['Run init and audit for this suite first.']})
            continue
        # Read and normalize the input data before build_workspace_status_site branches
        # on or transforms it further.
        data = json.loads(status_path.read_text(encoding='utf-8'))
        rows.append({'suite': suite, 'has_status': True, 'ok': bool(data.get('ok', False)), 'summary': data.get('summary', ''), 'next_steps': list(data.get('next_steps', []))[:5], 'warnings': list(data.get('warnings', []))[:5], 'command': data.get('command', ''), 'latest_run': data.get('latest_run')})
    return {
        'schema_version': 'fy.workspace-status-site.v1',
        'suite_count': len(rows),
        'ok_suite_count': sum(1 for row in rows if row['ok']),
        'blocked_suite_count': sum(1 for row in rows if not row['ok']),
        'suites': rows,
    }


def render_workspace_status_markdown(payload: dict[str, Any]) -> str:
    """Render workspace status markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '# fy Workspace Status Site',
        '',
        'This page uses simple language. It tells you where each suite stands right now and what to do next.',
        '',
        f"- suites: `{payload.get('suite_count', 0)}`",
        f"- ok_suite_count: `{payload.get('ok_suite_count', 0)}`",
        f"- blocked_suite_count: `{payload.get('blocked_suite_count', 0)}`",
        '',
    ]
    for row in payload.get('suites', []):
        lines.extend([
            f"## {row['suite']}",
            '',
            f"- ok: `{str(row.get('ok', False)).lower()}`",
            f"- latest_command: `{row.get('command', 'none')}`",
            f"- latest_run_id: `{(row.get('latest_run') or {}).get('run_id', 'none')}`",
            '',
        ])
        if row.get('summary'):
            lines.append(row['summary'])
            lines.append('')
        lines.append('### Most-Recent-Next-Steps')
        lines.append('')
        for step in row.get('next_steps', []) or ['Run the suite and generate a status page first.']:
            lines.append(f'- {step}')
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def write_workspace_status_site(workspace: Path, payload: dict[str, Any]) -> dict[str, str]:
    """Write workspace status site.

    This callable writes or records artifacts as part of its workflow.

    Args:
        workspace: Primary workspace used by this step.
        payload: Structured data carried through this workflow.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(workspace)
    write_platform_doc_artifacts(workspace, stem='workspace_status_site', json_payload=payload, markdown_text=render_workspace_status_markdown(payload))
    md_text = render_workspace_status_markdown(payload)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(workspace / 'docs' / 'platform' / 'WORKSPACE_STATUS_SITE.md', md_text)
    return {
        'workspace_status_site_json_path': str((workspace / 'docs' / 'platform' / 'workspace_status_site.json').relative_to(workspace)),
        'workspace_status_site_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_STATUS_SITE.md').relative_to(workspace)),
        'workspace_status_site_internal_json_path': str((workspace / 'docs' / 'platform' / 'workspace_status_site.json').relative_to(workspace)),
        'workspace_status_site_internal_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_STATUS_SITE.md').relative_to(workspace)),
    }
