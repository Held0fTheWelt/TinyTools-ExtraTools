"""Production readiness render for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.workspace import write_text, workspace_root, write_platform_doc_artifacts
from templatify.tools.rendering import render_standard_report


def _fallback_production_markdown(payload: dict[str, object]) -> str:
    """Fallback production markdown.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '# fy Workspace Production Readiness',
        '',
        f"- ok: `{str(payload['ok']).lower()}`",
        f"- schema_version: `{payload['schema_version']}`",
        f"- generated_at: `{payload['generated_at']}`",
        '',
        '## Top Next Steps',
        '',
    ]
    lines.extend(f'- {item}' for item in payload.get('top_next_steps', []))
    lines.extend([
        '', '## Persistence', '',
        f"- backup_count: `{payload['persistence']['backup_count']}`",
        f"- migrations_required: `{str(payload['persistence']['migration_plan']['required']).lower()}`",
        '', '## Compatibility', '',
        f"- command_envelope_current: `{payload['compatibility']['command_envelope']['current']}`",
        f"- manifest_current: `{payload['compatibility']['manifest']['current_manifest_version']}`",
        '', '## Observability', '',
        f"- command_event_count: `{payload['observability']['command_event_count']}`",
        f"- route_event_count: `{payload['observability']['route_event_count']}`",
        '', '## Security', '',
        f"- ok: `{str(payload['security']['ok']).lower()}`",
        f"- risky_file_count: `{payload['security']['risky_file_count']}`",
        f"- secret_hit_count: `{payload['security']['secret_hit_count']}`",
        '', '## Release Management', '',
        f"- ok: `{str(payload['release_management']['ok']).lower()}`",
        f"- missing_files: `{len(payload['release_management']['missing'])}`",
        '', '## Multi-repo Stability', '',
        f"- fixture_count: `{payload['multi_repo']['fixture_count']}`",
    ])
    return '\n'.join(lines).strip() + '\n'


def render_workspace_production_markdown(payload: dict[str, object], workspace: Path | None = None) -> str:
    """Render workspace production markdown.

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
        'schema_version': payload['schema_version'],
        'generated_at': payload['generated_at'],
        'top_next_steps_lines': '\n'.join(f'- {item}' for item in payload.get('top_next_steps', [])) or '- none',
        'persistence_lines': '\n'.join([f"- backup_count: `{payload['persistence']['backup_count']}`", f"- migrations_required: `{str(payload['persistence']['migration_plan']['required']).lower()}`"]),
        'compatibility_lines': '\n'.join([f"- command_envelope_current: `{payload['compatibility']['command_envelope']['current']}`", f"- manifest_current: `{payload['compatibility']['manifest']['current_manifest_version']}`"]),
        'observability_lines': '\n'.join([f"- command_event_count: `{payload['observability']['command_event_count']}`", f"- route_event_count: `{payload['observability']['route_event_count']}`"]),
        'security_lines': '\n'.join([f"- ok: `{str(payload['security']['ok']).lower()}`", f"- risky_file_count: `{payload['security']['risky_file_count']}`", f"- secret_hit_count: `{payload['security']['secret_hit_count']}`"]),
        'release_management_lines': '\n'.join([f"- ok: `{str(payload['release_management']['ok']).lower()}`", f"- missing_files: `{len(payload['release_management']['missing'])}`"]),
        'multi_repo_lines': f"- fixture_count: `{payload['multi_repo']['fixture_count']}`",
    }
    return render_standard_report(workspace or Path('.'), 'workspace_production_readiness', context, lambda: _fallback_production_markdown(payload))


def write_workspace_production_site(root: Path | None, payload: dict[str, object]) -> dict[str, str]:
    """Write workspace production site.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.
        payload: Structured data carried through this workflow.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    write_platform_doc_artifacts(workspace, stem='workspace_production_readiness', json_payload=payload, markdown_text=render_workspace_production_markdown(payload, workspace))
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(workspace / 'docs' / 'platform' / 'WORKSPACE_PRODUCTION_READINESS.md', render_workspace_production_markdown(payload, workspace))
    return {
        'workspace_production_json_path': str((workspace / 'docs' / 'platform' / 'workspace_production_readiness.json').relative_to(workspace)),
        'workspace_production_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_PRODUCTION_READINESS.md').relative_to(workspace)),
        'workspace_production_internal_json_path': str((workspace / 'docs' / 'platform' / 'workspace_production_readiness.json').relative_to(workspace)),
        'workspace_production_internal_md_path': str((workspace / 'docs' / 'platform' / 'WORKSPACE_PRODUCTION_READINESS.md').relative_to(workspace)),
    }
