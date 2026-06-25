"""Template inventory for templatify.tools.

"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXTENDS_RE = re.compile(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}')
BLOCK_RE = re.compile(r'{%\s*block\s+([A-Za-z0-9_]+)\s*%}(.*?){%\s*endblock(?:\s+[A-Za-z0-9_]+)?\s*%}', re.S)

AREA_DEFINITIONS: dict[str, dict[str, Any]] = {
    'frontend': {
        'target_root': 'frontend/templates',
        'base_template': 'base.html',
        'slot_map': {
            '[[TITLE]]': 'title',
            '[[EXTRA_HEAD]]': 'extra_head',
            '[[BODY_CLASS]]': 'body_class',
            '[[HEADER]]': 'site_header',
            '[[CONTENT]]': 'site_main',
            '[[EXTRA_SCRIPTS]]': 'extra_scripts',
        },
        'bridge_block': ('site_main', 'content'),
        'extends_aliases': ['base.html'],
    },
    'administration_tool': {
        'target_root': 'administration-tool/templates',
        'base_template': 'base.html',
        'slot_map': {
            '[[TITLE]]': 'title',
            '[[META_DESCRIPTION]]': 'meta_description',
            '[[EXTRA_HEAD]]': 'extra_head',
            '[[BODY_CLASS]]': 'body_class',
            '[[CONTENT]]': 'content',
            '[[EXTRA_SCRIPTS]]': 'extra_scripts',
        },
        'bridge_block': None,
        'extends_aliases': ['base.html'],
    },
    'administration_manage': {
        'target_root': 'administration-tool/templates/manage',
        'base_template': 'base.html',
        'slot_map': {
            '[[TITLE]]': 'title',
            '[[EXTRA_HEAD]]': 'extra_head',
            '[[CONTENT]]': 'content',
            '[[EXTRA_SCRIPTS]]': 'extra_scripts',
        },
        'bridge_block': None,
        'extends_aliases': ['manage/base.html', 'base.html'],
    },
    'backend_info': {
        'target_root': 'backend/app/info/templates',
        'base_template': 'base.html',
        'slot_map': {
            '[[TITLE]]': 'title',
            '[[WRAP_MODIFIERS]]': 'wrap_modifiers',
            '[[HEADING]]': 'heading',
            '[[SUBHEADING]]': 'subheading',
            '[[CONTENT]]': 'body',
        },
        'bridge_block': None,
        'extends_aliases': ['base.html'],
    },
    'writers_room': {
        'target_root': 'writers-room/app/templates',
        'base_template': 'base.html',
        'slot_map': {
            '[[TITLE]]': 'title',
            '[[EXTRA_HEAD]]': 'extra_head',
            '[[CONTENT]]': 'content',
        },
        'bridge_block': None,
        'extends_aliases': ['base.html'],
    },
}


@dataclass
class TemplateRecord:
    """Structured data container for template record.
    """
    path: str
    extends: str | None
    blocks: list[str]


def parse_template(text: str) -> dict[str, Any]:
    """Parse template.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    extends_match = EXTENDS_RE.search(text)
    extends = extends_match.group(1) if extends_match else None
    blocks = [match.group(1) for match in BLOCK_RE.finditer(text)]
    return {'extends': extends, 'blocks': blocks}


def scan_template_tree(root: Path) -> list[TemplateRecord]:
    """Scan template tree.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[TemplateRecord]:
            Collection produced from the parsed or
            accumulated input data.
    """
    records: list[TemplateRecord] = []
    for path in sorted(root.rglob('*.html')):
        parsed = parse_template(path.read_text(encoding='utf-8', errors='ignore'))
        records.append(TemplateRecord(path=path.relative_to(root).as_posix(), extends=parsed['extends'], blocks=parsed['blocks']))
    return records


def inspect_areas(repo_root: Path) -> dict[str, Any]:
    """Inspect areas.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    payload: dict[str, Any] = {'suite': 'templatify', 'areas': {}}
    for area, info in AREA_DEFINITIONS.items():
        target = repo_root / info['target_root']
        base_file = target / info['base_template']
        records = scan_template_tree(target) if target.is_dir() else []
        aliases = set(info.get('extends_aliases', [info['base_template']]))
        child_count = sum(1 for record in records if record.extends in aliases)
        base_blocks: list[str] = []
        if base_file.is_file():
            base_blocks = parse_template(base_file.read_text(encoding='utf-8', errors='ignore'))['blocks']
        payload['areas'][area] = {
            'target_root': info['target_root'],
            'base_template': info['base_template'],
            'exists': target.is_dir(),
            'template_count': len(records),
            'child_count_extending_base': child_count,
            'base_blocks': base_blocks,
            'records': [record.__dict__ for record in records],
            'slot_map': info['slot_map'],
            'bridge_block': info['bridge_block'],
        }
    return payload
