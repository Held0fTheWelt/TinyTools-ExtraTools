"""Template registry for templatify.tools.

"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

@dataclass
class TemplateRecord:
    """Structured data container for template record.
    """
    template_id: str
    family: str
    name: str
    path: str
    placeholders: list[str]
    sha256: str


def discover_templates(workspace_root: Path) -> list[TemplateRecord]:
    """Discover templates.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.

    Returns:
        list[TemplateRecord]:
            Collection produced from the parsed or
            accumulated input data.
    """
    base = workspace_root / 'templatify' / 'templates'
    records: list[TemplateRecord] = []
    # Branch on not base.is_dir() so discover_templates only continues along the
    # matching state path.
    if not base.is_dir():
        return records
    # Process path one item at a time so discover_templates applies the same rule across
    # the full collection.
    for path in sorted(base.rglob('*.tmpl')):
        # Read and normalize the input data before discover_templates branches on or
        # transforms it further.
        text = path.read_text(encoding='utf-8', errors='replace')
        family = path.relative_to(base).parts[0]
        rel = path.relative_to(base).as_posix()
        name = path.stem.replace('.md', '')
        placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
        records.append(TemplateRecord(
            template_id=f'{family}:{name}',
            family=family,
            name=name,
            path=rel,
            placeholders=placeholders,
            sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
        ))
    return records


def template_map(workspace_root: Path) -> dict[str, TemplateRecord]:
    """Template map.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, TemplateRecord]:
            Structured payload describing the outcome of the
            operation.
    """
    return {item.template_id: item for item in discover_templates(workspace_root)}
