"""Status page rendering for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.status_page_analysis import simple_governance_lines
from fy_platform.ai.workspace import write_json, write_text
from templatify.tools.rendering import render_standard_report


def _fallback_markdown(status: dict[str, Any]) -> str:
    """Fallback markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        status: Named status for this operation.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    latest = status.get('latest_run') or {}
    lines = [
        f"# {status['suite']} — Most-Recent-Next-Steps",
        '',
        'This page uses simple language. It should help you understand the latest result and what to do next.',
        '',
        '## Current status',
        '',
        f"- suite: `{status['suite']}`",
        f"- command: `{status['command']}`",
        f"- ok: `{str(status['ok']).lower()}`",
        f"- latest_run_id: `{latest.get('run_id', 'none')}`",
        f"- latest_run_mode: `{latest.get('mode', 'none')}`",
        f"- latest_run_status: `{latest.get('status', 'none')}`",
        '',
    ]
    # Branch on status.get('summary') so _fallback_markdown only continues along the
    # matching state path.
    if status.get('summary'):
        lines.extend(['## Plain summary', '', str(status['summary']), ''])
    # Branch on status.get('decision_summary') so _fallback_markdown only continues
    # along the matching state path.
    if status.get('decision_summary'):
        lines.extend(['## Decision guidance', '', str(status['decision_summary']), ''])
    lines.extend(['## Most-Recent-Next-Steps', ''])
    lines.extend(f'- {item}' for item in status.get('next_steps', []))
    lines.append('')
    lines.extend(['## Key signals', ''])
    # Process (key, value) one item at a time so _fallback_markdown applies the same
    # rule across the full collection.
    for key, value in (status.get('key_signals') or {}).items():
        lines.append(f'- {key}: `{value}`')
    lines.append('')
    # Branch on status.get('uncertainty') so _fallback_markdown only continues along the
    # matching state path.
    if status.get('uncertainty'):
        lines.extend(['## Uncertainty', ''])
        lines.extend(f'- {item}' for item in status['uncertainty'])
        lines.append('')
    cross = status.get('cross_suite') or {}
    # Branch on cross.get('signals') so _fallback_markdown only continues along the
    # matching state path.
    if cross.get('signals'):
        lines.extend(['## Cross-suite signals', ''])
        # Process signal one item at a time so _fallback_markdown applies the same rule
        # across the full collection.
        for signal in cross['signals']:
            lines.append(f"- `{signal['suite']}`: {signal.get('status_summary') or 'No summary available.'}")
            # Process step one item at a time so _fallback_markdown applies the same
            # rule across the full collection.
            for step in signal.get('next_steps', [])[:2]:
                lines.append(f'  - next: {step}')
        lines.append('')
    governance_lines = simple_governance_lines(status.get('governance'))
    # Branch on governance_lines so _fallback_markdown only continues along the matching
    # state path.
    if governance_lines:
        lines.extend(['## Governance', ''])
        lines.extend(governance_lines)
        lines.append('')
    warnings = status.get('warnings', []) or []
    # Branch on warnings so _fallback_markdown only continues along the matching state
    # path.
    if warnings:
        lines.extend(['## Warnings', ''])
        lines.extend(f'- {item}' for item in warnings)
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def _status_context(status: dict[str, Any]) -> dict[str, Any]:
    """Status context.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        status: Named status for this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    latest = status.get('latest_run') or {}
    cross_lines: list[str] = []
    for signal in (status.get('cross_suite') or {}).get('signals', []):
        cross_lines.append(f"- `{signal['suite']}`: {signal.get('status_summary') or 'No summary available.'}")
        cross_lines.extend(f"  - next: {step}" for step in signal.get('next_steps', [])[:2])
    return {
        'suite': status['suite'],
        'command': status['command'],
        'ok': str(status['ok']).lower(),
        'latest_run_id': latest.get('run_id', 'none'),
        'latest_run_mode': latest.get('mode', 'none'),
        'latest_run_status': latest.get('status', 'none'),
        'summary': status.get('summary', 'No summary is available yet.'),
        'decision_summary': status.get('decision_summary', ''),
        'next_steps_lines': '\n'.join(f'- {item}' for item in status.get('next_steps', [])) or '- none',
        'key_signal_lines': '\n'.join(f"- {key}: `{value}`" for key, value in (status.get('key_signals') or {}).items()) or '- none',
        'uncertainty_lines': '\n'.join(f'- {item}' for item in status.get('uncertainty', [])) or '- none',
        'cross_suite_lines': '\n'.join(cross_lines) or '- none',
        'governance_lines': '\n'.join(simple_governance_lines(status.get('governance'))) or '- none',
        'warnings_lines': '\n'.join(f'- {item}' for item in status.get('warnings', [])) or '- none',
    }


def render_status_markdown(status: dict[str, Any], workspace_root: Path | None = None) -> str:
    """Render status markdown.

    Args:
        status: Named status for this operation.
        workspace_root: Root directory used to resolve repository-local
            paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    root = workspace_root or Path('.')
    return render_standard_report(root, 'status_summary', _status_context(status), lambda: _fallback_markdown(status))


def write_status_page(workspace_root: Path, suite: str, status: dict[str, Any]) -> dict[str, str]:
    """Write status page.

    This callable writes or records artifacts as part of its workflow.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        suite: Primary suite used by this step.
        status: Named status for this operation.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    base = workspace_root / suite / 'reports' / 'status'
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / 'most_recent_next_steps.json'
    md_path = base / 'MOST_RECENT_NEXT_STEPS.md'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(json_path, status)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(md_path, render_status_markdown(status, workspace_root=workspace_root))
    return {'status_json_path': str(json_path.relative_to(workspace_root)), 'status_md_path': str(md_path.relative_to(workspace_root))}
