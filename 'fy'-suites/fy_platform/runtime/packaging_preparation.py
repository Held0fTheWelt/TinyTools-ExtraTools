"""Packaging preparation for fy_platform.runtime.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json, write_text, workspace_root
from fy_platform.surfaces.alias_map import build_surface_alias_payload
from templatify.tools.rendering import render_standard_report

TARGET_LAYOUT = [
    'fy_platform/core/* for workspace, hashing, IO, and backup primitives.',
    'fy_platform/runtime/* for mode dispatch, lane runtime, compatibility routing, and transition stabilization.',
    'fy_platform/ir/* for models, IDs, catalog persistence, relations, and serializers.',
    'fy_platform/providers/* for provider contracts, governor, cache, execution, and adapters.',
    'fy_platform/surfaces/* for platform shell, legacy aliases, lens registry, alias maps, and public shell docs.',
    'fy_platform/services/* for domain services separated from platform runtime concerns.',
    'fy_platform/compatibility/* for bounded carry-over shells during collapse.',
]

MIGRATION_NOTES = [
    'Keep fy_platform/ai as a compatibility shell during the staged move into core/runtime/ir/providers/surfaces.',
    'Prefer extraction over file moves when preserving import stability for runner-driven implementation passes.',
    'Do not remove legacy suite CLIs until surface aliases are documented and the platform shell covers the same outward action.',
    'Use despaghettify core-transition waves to decide extraction order for shared hotspots.',
]

FREEZE_CHECKLIST = [
    'Platform shell covers primary public entry points.',
    'Lane runtime persists real execution records for active platform modes.',
    'IR seed objects are written by real runtime paths.',
    'Governor boundary blocks or records every routed provider decision.',
    'Surface alias map is complete or explicitly excepted.',
    'Packaging impact reviewed for every still-public suite CLI.',
]


def build_packaging_preparation_payload(root: Path | None = None) -> dict[str, Any]:
    """Build packaging preparation payload.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # build_packaging_preparation_payload.
    workspace = workspace_root(root)
    alias_payload = build_surface_alias_payload(workspace)
    compatibility_impact = [
        {'surface': row['legacy_surface'], 'impact': 'compatibility-wrapper-retained', 'target': row['current_surface'], 'sunset_phase': row['sunset_phase']}
        for row in alias_payload['entries']
    ]
    return {
        'ok': True,
        'workspace_root': str(workspace),
        'target_layout': TARGET_LAYOUT,
        'migration_notes': MIGRATION_NOTES,
        'compatibility_impact_matrix': compatibility_impact,
        'package_freeze_checklist': FREEZE_CHECKLIST,
    }


def render_packaging_preparation_markdown(payload: dict[str, Any], root: Path | None = None) -> str:
    """Render packaging preparation markdown.

    Args:
        payload: Structured data carried through this workflow.
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    context = {
        'target_layout_lines': '\n'.join(f'- {item}' for item in payload.get('target_layout', [])) or '- none',
        'migration_note_lines': '\n'.join(f'- {item}' for item in payload.get('migration_notes', [])) or '- none',
        'compatibility_impact_lines': '\n'.join(f"- `{row['surface']}` → `{row['target']}` [{row['impact']}, {row['sunset_phase']}]" for row in payload.get('compatibility_impact_matrix', [])) or '- none',
        'freeze_check_lines': '\n'.join(f'- {item}' for item in payload.get('package_freeze_checklist', [])) or '- none',
    }
    def fallback() -> str:
        """Fallback the requested operation.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        lines = ['# fy Packaging Preparation Bundle', '', '## Target layout', '']
        lines.extend(context['target_layout_lines'].splitlines())
        lines.extend(['', '## Migration notes', ''])
        lines.extend(context['migration_note_lines'].splitlines())
        lines.extend(['', '## Compatibility impact matrix', ''])
        lines.extend(context['compatibility_impact_lines'].splitlines())
        lines.extend(['', '## Package freeze checklist', ''])
        lines.extend(context['freeze_check_lines'].splitlines())
        return '\n'.join(lines).strip() + '\n'
    return render_standard_report(root or Path('.'), 'packaging_preparation_bundle', context, fallback)


def write_packaging_preparation_bundle(root: Path | None = None) -> dict[str, Any]:
    """Write packaging preparation bundle.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    payload = build_packaging_preparation_payload(workspace)
    docs_dir = workspace / 'docs' / 'platform'
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / 'fy_v2_packaging_preparation_bundle.json'
    md_path = docs_dir / 'fy_v2_packaging_preparation_bundle.md'
    matrix_path = docs_dir / 'fy_v2_compatibility_impact_matrix.md'
    checklist_path = docs_dir / 'fy_v2_package_freeze_checklist.md'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(json_path, payload)
    markdown = render_packaging_preparation_markdown(payload, workspace)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(md_path, markdown)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(matrix_path, '## Compatibility impact matrix\n\n' + '\n'.join(f"- `{row['surface']}` → `{row['target']}` [{row['impact']}, {row['sunset_phase']}]" for row in payload['compatibility_impact_matrix']) + '\n')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(checklist_path, '## Package freeze checklist\n\n' + '\n'.join(f'- {item}' for item in payload['package_freeze_checklist']) + '\n')
    return {**payload, 'json_path': str(json_path.relative_to(workspace)), 'md_path': str(md_path.relative_to(workspace)), 'matrix_path': str(matrix_path.relative_to(workspace)), 'checklist_path': str(checklist_path.relative_to(workspace))}
