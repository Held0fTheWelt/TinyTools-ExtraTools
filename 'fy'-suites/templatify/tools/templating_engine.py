"""Templating engine for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from templatify.tools.template_inventory import AREA_DEFINITIONS, BLOCK_RE, inspect_areas


def _find_source_shell(source_dir: Path, area: str) -> Path | None:
    """Find source shell.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source_dir: Root directory used to resolve repository-local
            paths.
        area: Primary area used by this step.

    Returns:
        Path | None:
            Filesystem path produced or resolved by this
            callable.
    """
    candidates = [
        source_dir / area / 'shell.html',
        source_dir / 'default' / 'shell.html',
        source_dir / 'shell.html',
    ]
    # Process candidate one item at a time so _find_source_shell applies the same rule
    # across the full collection.
    for candidate in candidates:
        # Branch on candidate.is_file() so _find_source_shell only continues along the
        # matching state path.
        if candidate.is_file():
            return candidate
    return None


def _render_shell(shell_text: str, slot_map: dict[str, str]) -> str:
    """Render shell.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        shell_text: Primary shell text used by this step.
        slot_map: Primary slot map used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    rendered = shell_text
    for token, block_name in slot_map.items():
        replacement = '{% block ' + block_name + ' %}{% endblock %}'
        rendered = rendered.replace(token, replacement)
    return rendered


def _extract_block_defaults(base_text: str) -> dict[str, str]:
    """Extract block defaults.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        base_text: Primary base text used by this step.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    defaults: dict[str, str] = {}
    for match in BLOCK_RE.finditer(base_text):
        defaults[match.group(1)] = match.group(2).strip('\n')
    return defaults


def _render_adapter(area: str, shell_rel: str, base_text: str, bridge_block: tuple[str, str] | None) -> str:
    """Render adapter.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        area: Primary area used by this step.
        shell_rel: Primary shell rel used by this step.
        base_text: Primary base text used by this step.
        bridge_block: Primary bridge block used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    defaults = _extract_block_defaults(base_text)
    slot_map = AREA_DEFINITIONS[area]['slot_map']
    lines = [f'{{% extends "{shell_rel}" %}}', '']
    handled: set[str] = set()
    if bridge_block:
        parent_block, child_block = bridge_block
        lines.append('{% block ' + parent_block + ' %}')
        lines.append('  {% block ' + child_block + ' %}{% endblock %}')
        lines.append('{% endblock %}')
        lines.append('')
        handled.add(parent_block)
        handled.add(child_block)
    for block_name in sorted(set(slot_map.values())):
        if block_name in handled:
            continue
        body = defaults.get(block_name, '').strip()
        lines.append('{% block ' + block_name + ' %}')
        if body:
            lines.append(body)
        lines.append('{% endblock %}')
        lines.append('')
        handled.add(block_name)
    for block_name, body in defaults.items():
        if block_name in handled:
            continue
        lines.append('{% block ' + block_name + ' %}')
        if body.strip():
            lines.append(body.strip())
        lines.append('{% endblock %}')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def build_plan(repo_root: Path, source_dir: Path, areas: list[str] | None = None) -> dict[str, Any]:
    """Build plan.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        source_dir: Root directory used to resolve repository-local
            paths.
        areas: Primary areas used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    inventory = inspect_areas(repo_root)
    selected = areas or list(AREA_DEFINITIONS.keys())
    plan: dict[str, Any] = {'suite': 'templatify', 'source_dir': source_dir.as_posix(), 'areas': {}, 'warnings': []}
    for area in selected:
        info = AREA_DEFINITIONS[area]
        area_inventory = inventory['areas'][area]
        shell = _find_source_shell(source_dir, area)
        if not area_inventory['exists']:
            plan['warnings'].append(f'{area}: target root missing')
            continue
        if shell is None:
            plan['warnings'].append(f'{area}: no source shell found')
            plan['areas'][area] = {'status': 'missing_source_shell'}
            continue
        base_path = repo_root / info['target_root'] / info['base_template']
        if not base_path.is_file():
            plan['warnings'].append(f'{area}: base template missing')
            plan['areas'][area] = {'status': 'missing_base_template'}
            continue
        shell_text = shell.read_text(encoding='utf-8')
        generated_shell = _render_shell(shell_text, info['slot_map'])
        shell_rel = '_templatify/shell.html'
        adapter = _render_adapter(area, shell_rel, base_path.read_text(encoding='utf-8'), info['bridge_block'])
        target_dir = Path(info['target_root'])
        mapped_blocks = set(info['slot_map'].values())
        if info.get('bridge_block'):
            mapped_blocks.update(info['bridge_block'])
        unmapped_blocks = sorted(set(area_inventory['base_blocks']) - mapped_blocks)
        if unmapped_blocks:
            plan['warnings'].append(f"{area}: unmapped base blocks -> {', '.join(unmapped_blocks)}")
        plan['areas'][area] = {
            'status': 'ready',
            'target_root': info['target_root'],
            'base_template': info['base_template'],
            'source_shell': shell.relative_to(source_dir).as_posix(),
            'generated_shell_path': (target_dir / '_templatify' / 'shell.html').as_posix(),
            'generated_base_path': (target_dir / info['base_template']).as_posix(),
            'base_blocks': area_inventory['base_blocks'],
            'child_count_extending_base': area_inventory['child_count_extending_base'],
            'unmapped_base_blocks': unmapped_blocks,
            'generated_shell': generated_shell,
            'generated_base': adapter,
        }
    return plan


def apply_plan(repo_root: Path, plan: dict[str, Any], write_under_generated: bool = False) -> list[str]:
    """Apply plan.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        plan: Primary plan used by this step.
        write_under_generated: Whether to enable this optional behavior.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    written: list[str] = []
    for area, info in plan.get('areas', {}).items():
        if info.get('status') != 'ready':
            continue
        shell_path = repo_root / info['generated_shell_path']
        base_path = repo_root / info['generated_base_path']
        if write_under_generated:
            shell_path = repo_root / "'fy'-suites" / 'templatify' / 'generated' / area / info['generated_shell_path']
            base_path = repo_root / "'fy'-suites" / 'templatify' / 'generated' / area / info['generated_base_path']
        shell_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        shell_path.write_text(info['generated_shell'], encoding='utf-8')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        base_path.write_text(info['generated_base'], encoding='utf-8')
        written.append(shell_path.relative_to(repo_root).as_posix())
        written.append(base_path.relative_to(repo_root).as_posix())
    return written
