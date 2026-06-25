"""Template resolver for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path

from templatify.tools.template_registry import discover_templates


def resolve_template_path(workspace_root: Path, family: str, name: str) -> Path:
    """Resolve template path.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        family: Primary family used by this step.
        name: Primary name used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    base = workspace_root / 'templatify' / 'templates'
    candidates = [base / family / f'{name}.md.tmpl', base / family / f'{name}.tmpl']
    # Process candidate one item at a time so resolve_template_path applies the same
    # rule across the full collection.
    for candidate in candidates:
        # Branch on candidate.is_file() so resolve_template_path only continues along
        # the matching state path.
        if candidate.is_file():
            return candidate
    available = ', '.join(sorted(item.template_id for item in discover_templates(workspace_root) if item.family == family))
    raise FileNotFoundError(f'No template for family={family!r} name={name!r}. Available: {available}')
