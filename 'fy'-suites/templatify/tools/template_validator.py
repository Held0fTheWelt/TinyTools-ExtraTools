"""Template validator for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path

from templatify.tools.template_registry import discover_templates

REQUIRED_FAMILIES = {'documentify', 'reports', 'context_packs'}


def validate_templates(workspace_root: Path) -> dict:
    """Validate templates.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    records = discover_templates(workspace_root)
    template_ids = [item.template_id for item in records]
    duplicates = sorted({tid for tid in template_ids if template_ids.count(tid) > 1})
    families = sorted({item.family for item in records})
    missing_families = sorted(REQUIRED_FAMILIES - set(families))
    empty_templates = []
    # Process item one item at a time so validate_templates applies the same rule across
    # the full collection.
    for item in records:
        path = workspace_root / 'templatify' / 'templates' / item.path
        # Branch on not path.read_text(encoding='utf-8', errors='... so
        # validate_templates only continues along the matching state path.
        if not path.read_text(encoding='utf-8', errors='replace').strip():
            empty_templates.append(item.template_id)
    warnings = []
    # Branch on any(('role' in item.name for item in records)... so validate_templates
    # only continues along the matching state path.
    if any('role' in item.name for item in records) and not any('role_summary' in item.placeholders for item in records if 'role' in item.name):
        warnings.append('role_templates_without_role_summary_placeholder')
    return {
        'ok': not duplicates and not missing_families and not empty_templates and bool(records),
        'template_count': len(records),
        'families': families,
        'duplicates': duplicates,
        'missing_families': missing_families,
        'empty_templates': empty_templates,
        'warnings': warnings,
    }
