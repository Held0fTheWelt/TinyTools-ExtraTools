"""Alias map for fy_platform.surfaces.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json, write_text, workspace_root
from fy_platform.runtime.mode_registry import MODE_SPECS
from fy_platform.surfaces.legacy_aliases import LEGACY_ALIAS_MAP
from templatify.tools.rendering import render_standard_report

LENS_GROUPS = {
    'governance': ['contract', 'security', 'release', 'production'],
    'quality': ['quality', 'structure'],
    'knowledge': ['docs', 'code_docs'],
    'platform': ['context_pack', 'mvp', 'report', 'governor_status', 'surface_aliases', 'packaging_prep'],
}

EXPLICIT_EXCEPTIONS = [
    'dockerify remains suite-first until provider/runtime packaging converges.',
    'postmanify remains suite-first until API projection governance is explicitly collapsed.',
    'observifyfy stays internal-first and is not yet exposed as a platform mode.',
    'usabilify remains indirectly represented through the knowledge lens until its collapse surface is implemented.',
]


def build_surface_alias_payload(root: Path | None = None) -> dict[str, Any]:
    """Build surface alias payload.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    entries = []
    # Process (legacy, current) one item at a time so build_surface_alias_payload
    # applies the same rule across the full collection.
    for legacy, current in sorted(LEGACY_ALIAS_MAP.items()):
        fy_name, public_command, mode_name = current
        spec_key = f'{public_command}.{mode_name}'
        spec = MODE_SPECS.get(spec_key)
        entries.append({
            'legacy_surface': legacy,
            'current_surface': f'{fy_name} {public_command} --mode {mode_name}',
            'lens': spec.lens if spec else 'platform',
            'sunset_phase': 'C2' if legacy not in {'dockerify', 'postmanify'} else 'C3',
            'status': 'compatibility-entry',
        })
    return {
        'ok': True,
        'workspace_root': str(workspace),
        'entry_count': len(entries),
        'entries': entries,
        'lens_groups': LENS_GROUPS,
        'exceptions': EXPLICIT_EXCEPTIONS,
    }


def render_surface_alias_markdown(payload: dict[str, Any], root: Path | None = None) -> str:
    """Render surface alias markdown.

    Args:
        payload: Structured data carried through this workflow.
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    context = {
        'entry_count': payload['entry_count'],
        'lens_lines': '\n'.join(f"- `{lens}`: {', '.join(modes)}" for lens, modes in payload.get('lens_groups', {}).items()) or '- none',
        'alias_lines': '\n'.join(f"- `{row['legacy_surface']}` → `{row['current_surface']}` [{row['lens']}, {row['sunset_phase']}]" for row in payload.get('entries', [])) or '- none',
        'exception_lines': '\n'.join(f'- {item}' for item in payload.get('exceptions', [])) or '- none',
    }
    def fallback() -> str:
        """Fallback the requested operation.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        lines = ['# fy Surface Alias Map', '', f"- entry_count: `{payload['entry_count']}`", '', '## Lenses', '']
        lines.extend(context['lens_lines'].splitlines())
        lines.extend(['', '## Legacy alias entries', ''])
        lines.extend(context['alias_lines'].splitlines())
        lines.extend(['', '## Explicit exceptions', ''])
        lines.extend(context['exception_lines'].splitlines())
        return '\n'.join(lines).strip() + '\n'
    return render_standard_report(root or Path('.'), 'surface_aliases', context, fallback)


def write_surface_alias_artifacts(root: Path | None = None) -> dict[str, Any]:
    """Write surface alias artifacts.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    payload = build_surface_alias_payload(workspace)
    docs_dir = workspace / 'docs' / 'platform'
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / 'fy_v2_surface_aliases.json'
    md_path = docs_dir / 'fy_v2_surface_aliases.md'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(json_path, payload)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(md_path, render_surface_alias_markdown(payload, workspace))
    return {**payload, 'json_path': str(json_path.relative_to(workspace)), 'md_path': str(md_path.relative_to(workspace))}
