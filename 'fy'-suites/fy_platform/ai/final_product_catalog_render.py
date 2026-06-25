"""Final product catalog render for fy_platform.ai.

"""
from __future__ import annotations


def render_suite_catalog_markdown(payload: dict[str, object]) -> str:
    """Render suite catalog markdown.

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
        '# fy Suite Catalog',
        '',
        'This is the product-facing catalog of all suites currently present in the autark fy workspace.',
        '',
        f"- suite_count: `{payload.get('suite_count', 0)}`",
        f"- core_count: `{payload.get('core_count', 0)}`",
        f"- optional_count: `{payload.get('optional_count', 0)}`",
        '',
    ]
    # Process row one item at a time so render_suite_catalog_markdown applies the same
    # rule across the full collection.
    for row in payload.get('suites', []):
        lines.extend([
            f"## {row['suite']}",
            '',
            f"- category: `{row['category']}`",
            f"- quality_ok: `{str(row['quality_ok']).lower()}`",
            f"- release_ready: `{str(row['release_ready']).lower()}`",
            f"- latest_run_id: `{row.get('latest_run_id') or 'none'}`",
            '',
            row['summary'],
            '',
            '### Lifecycle commands',
            '',
        ])
        lines.extend(f"- `{cmd}`" for cmd in row.get('lifecycle_commands', []))
        # Branch on row.get('native_commands') so render_suite_catalog_markdown only
        # continues along the matching state path.
        if row.get('native_commands'):
            lines.extend(['', '### Native commands', ''])
            lines.extend(f"- `{cmd}`" for cmd in row['native_commands'])
        # Branch on row.get('quality_missing') so render_suite_catalog_markdown only
        # continues along the matching state path.
        if row.get('quality_missing'):
            lines.extend(['', '### Missing required surfaces', ''])
            lines.extend(f"- `{item}`" for item in row['quality_missing'])
        # Branch on row.get('quality_warnings') so render_suite_catalog_markdown only
        # continues along the matching state path.
        if row.get('quality_warnings'):
            lines.extend(['', '### Warnings', ''])
            lines.extend(f"- `{item}`" for item in row['quality_warnings'])
        lines.append('')
    return '\n'.join(lines).strip() + '\n'


def render_command_reference_markdown(payload: dict[str, object]) -> str:
    """Render command reference markdown.

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
        '# fy Command Reference',
        '',
        'This page lists the stable shared lifecycle commands and the suite-specific native commands.',
        '',
        f"- command_envelope_current: `{payload['command_envelope_current']}`",
        f"- supported_read_versions: `{', '.join(payload['command_envelope_compatibility']['supported_read_versions'])}`",
        f"- supported_write_versions: `{', '.join(payload['command_envelope_compatibility']['supported_write_versions'])}`",
        '',
        f"- active_strategy_profile: `{payload.get('active_strategy_profile', {}).get('active_profile', '')}`",
        '',
        '## Platform-native commands',
        '',
    ]
    lines.extend(f"- `{cmd}`" for cmd in payload.get('platform_native_commands', []))
    lines.extend(['', '## Generic lifecycle commands', ''])
    lines.extend(f"- `{cmd}`" for cmd in payload.get('generic_lifecycle_commands', []))
    lines.extend(['', '## Suite-native commands', ''])
    for suite, commands in payload.get('suite_native_commands', {}).items():
        lines.extend([f'### {suite}', ''])
        if commands:
            lines.extend(f"- `{cmd}`" for cmd in commands)
        else:
            lines.append('- no additional native commands')
        lines.append('')
    return '\n'.join(lines).strip() + '\n'
