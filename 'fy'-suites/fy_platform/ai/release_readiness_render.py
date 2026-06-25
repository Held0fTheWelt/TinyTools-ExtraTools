"""Release readiness render for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.policy.suite_quality_policy import CORE_SUITES, OPTIONAL_SUITES
from fy_platform.ai.workspace import write_text, workspace_root, write_platform_doc_artifacts
from templatify.tools.rendering import render_standard_report


def _suite_lines(payload: dict[str, object], allowed: list[str]) -> list[str]:
    """Suite lines.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        payload: Structured data carried through this workflow.
        allowed: Primary allowed used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    lines: list[str] = []
    # Process row one item at a time so _suite_lines applies the same rule across the
    # full collection.
    for row in payload.get('suites', []):
        # Branch on row['suite'] not in allowed so _suite_lines only continues along the
        # matching state path.
        if row['suite'] not in allowed:
            continue
        lines.append(f"- `{row['suite']}` ready=`{str(row['ready']).lower()}` latest_run=`{(row['latest_run'] or {}).get('run_id', 'none')}`")
        lines.extend(f"  - blocking: `{reason}`" for reason in row.get('blocking_reasons', []))
        lines.extend(f"  - next: {step}" for step in row.get('next_steps', [])[:3])
    return lines


def _fallback_release_markdown(payload: dict[str, object]) -> str:
    """Fallback release markdown.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '# fy Workspace Release Readiness',
        '',
        f"- ok: `{str(payload['ok']).lower()}`",
        f"- generated_at: `{payload['generated_at']}`",
        f"- core_ready: `{len(payload.get('core_ready_suites', []))}`",
        f"- core_blocked: `{len(payload.get('core_blocked_suites', []))}`",
        '',
        '## Core suites',
        '',
    ]
    lines.extend(_suite_lines(payload, CORE_SUITES) or ['- none'])
    if payload.get('optional_ready_suites') or payload.get('optional_blocked_suites'):
        lines.extend(['', '## Optional suites', ''])
        lines.extend(_suite_lines(payload, OPTIONAL_SUITES) or ['- none'])
    return '\n'.join(lines).strip() + '\n'


def render_workspace_release_markdown(payload: dict[str, object], workspace: Path | None = None) -> str:
    """Render workspace release markdown.

    Args:
        payload: Structured data carried through this workflow.
        workspace: Primary workspace used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    context = {
        'ok': str(payload['ok']).lower(),
        'generated_at': payload['generated_at'],
        'core_ready_count': len(payload.get('core_ready_suites', [])),
        'core_blocked_count': len(payload.get('core_blocked_suites', [])),
        'core_suite_lines': '\n'.join(_suite_lines(payload, CORE_SUITES)) or '- none',
        'optional_suite_lines': '\n'.join(_suite_lines(payload, OPTIONAL_SUITES)) or '- none',
    }
    return render_standard_report(workspace or Path('.'), 'workspace_release_readiness', context, lambda: _fallback_release_markdown(payload))


def write_workspace_release_site(workspace: Path, payload: dict[str, object]) -> dict[str, str]:
    """Write workspace release site.

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
    write_platform_doc_artifacts(workspace, stem='workspace_release_readiness', json_payload=payload, markdown_text=render_workspace_release_markdown(payload, workspace))
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(workspace / 'docs' / 'platform' / 'WORKSPACE_RELEASE_READINESS.md', render_workspace_release_markdown(payload, workspace))
    return {
        'workspace_status_json_path': str((workspace / 'docs' / 'platform' / 'workspace_release_readiness.json').relative_to(workspace)),
        'workspace_status_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_RELEASE_READINESS.md').relative_to(workspace)),
        'workspace_status_internal_json_path': str((workspace / 'docs' / 'platform' / 'workspace_release_readiness.json').relative_to(workspace)),
        'workspace_status_internal_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_RELEASE_READINESS.md').relative_to(workspace)),
    }
