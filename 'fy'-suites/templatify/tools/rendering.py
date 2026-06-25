"""Rendering for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from templatify.tools.template_registry import template_map
from templatify.tools.template_render import render_with_header


REPORT_SCHEMA_FIELDS = {
    'status_summary': ['suite', 'command', 'ok', 'summary', 'next_steps_lines', 'warnings_lines', 'uncertainty_lines', 'cross_suite_lines'],
    'workspace_release_readiness': ['ok', 'generated_at', 'core_ready_count', 'core_blocked_count', 'core_suite_lines', 'optional_suite_lines'],
    'workspace_production_readiness': ['ok', 'schema_version', 'generated_at', 'top_next_steps_lines', 'persistence_lines', 'compatibility_lines', 'observability_lines', 'security_lines', 'release_management_lines', 'multi_repo_lines'],
    'surface_aliases': ['entry_count', 'lens_lines', 'alias_lines', 'exception_lines'],
    'packaging_preparation_bundle': ['target_layout_lines', 'migration_note_lines', 'compatibility_impact_lines', 'freeze_check_lines'],
}


def report_schema(report_kind: str) -> dict[str, Any]:
    """Report schema.

    Args:
        report_kind: Primary report kind used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {'report_kind': report_kind, 'fields': REPORT_SCHEMA_FIELDS.get(report_kind, []), 'template_preferred': True}


def render_standard_report(workspace_root: Path, report_kind: str, context: dict[str, Any], fallback: Callable[[], str]) -> str:
    """Render standard report.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        report_kind: Primary report kind used by this step.
        context: Primary context used by this step.
        fallback: Primary fallback used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    records = template_map(workspace_root)
    template_id = f'reports:{report_kind}'
    # Branch on template_id in records so render_standard_report only continues along
    # the matching state path.
    if template_id in records:
        rendered, _ = render_with_header(workspace_root, 'reports', report_kind, context)
        return rendered
    return fallback()
