"""Template render for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path

from templatify.tools.template_registry import discover_templates
from templatify.tools.template_resolver import resolve_template_path


class SafeDict(dict):
    """Coordinate safe dict behavior.
    """
    def __missing__(self, key: str) -> str:
        """Missing the requested operation.

        Args:
            key: Primary key used by this step.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        return '{' + key + '}'


def render_template_text(template_text: str, context: dict[str, object]) -> str:
    """Render template text.

    Args:
        template_text: Primary template text used by this step.
        context: Primary context used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    normalized = {k: ('' if v is None else str(v)) for k, v in context.items()}
    return template_text.format_map(SafeDict(normalized))


def render_template(workspace_root: Path, family: str, name: str, context: dict[str, object]):
    """Render template.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        family: Primary family used by this step.
        name: Primary name used by this step.
        context: Primary context used by this step.
    """
    records = {item.template_id: item for item in discover_templates(workspace_root)}
    path = resolve_template_path(workspace_root, family, name)
    key = f'{family}:{path.stem.replace(".md", "")}'
    record = records[key]
    rendered = render_template_text(path.read_text(encoding='utf-8', errors='replace'), context)
    return rendered, record


def render_with_header(workspace_root: Path, family: str, name: str, context: dict[str, object]):
    """Render with header.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        family: Primary family used by this step.
        name: Primary name used by this step.
        context: Primary context used by this step.
    """
    rendered, record = render_template(workspace_root, family, name, context)
    header = f'<!-- templify:template_id={record.template_id} template_hash={record.sha256} -->\n'
    return header + rendered, record
