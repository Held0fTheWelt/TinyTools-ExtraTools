"""Workspace docs for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace_io import write_json, write_text
from fy_platform.ai.workspace_layout import internal_platform_docs_root, internal_root, workspace_root


def write_platform_doc_artifacts(
    workspace: Path,
    *,
    stem: str,
    json_payload: Any | None = None,
    markdown_text: str | None = None,
) -> dict[str, str | None]:
    """Write platform doc artifacts.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace: Primary workspace used by this step.
        stem: Primary stem used by this step.
        json_payload: Primary json payload used by this step.
        markdown_text: Primary markdown text used by this step.

    Returns:
        dict[str, str | None]:
            Structured payload describing the outcome of the
            operation.
    """
    # Build filesystem locations and shared state that the rest of
    # write_platform_doc_artifacts reuses.
    workspace = workspace_root(workspace)
    out_dir = internal_platform_docs_root(workspace)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_rel = md_rel = None
    # Branch on json_payload is not None so write_platform_doc_artifacts only continues
    # along the matching state path.
    if json_payload is not None:
        out_json = out_dir / f'{stem}.json'
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(out_json, json_payload)
        json_rel = str(out_json.relative_to(workspace))
    # Branch on markdown_text is not None so write_platform_doc_artifacts only continues
    # along the matching state path.
    if markdown_text is not None:
        out_md = out_dir / f'{stem}.md'
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        write_text(out_md, markdown_text)
        md_rel = str(out_md.relative_to(workspace))

    internal_platform = internal_root(workspace) / 'docs' / 'platform'
    internal_platform.mkdir(parents=True, exist_ok=True)
    # Branch on json_payload is not None so write_platform_doc_artifacts only continues
    # along the matching state path.
    if json_payload is not None:
        write_json(internal_platform / f'{stem}.json', json_payload)
    # Branch on markdown_text is not None so write_platform_doc_artifacts only continues
    # along the matching state path.
    if markdown_text is not None:
        write_text(internal_platform / f'{stem}.md', markdown_text)
    return {
        'json_path': json_rel,
        'md_path': md_rel,
        'canonical_json_path': json_rel,
        'canonical_md_path': md_rel,
        'legacy_json_path': json_rel,
        'legacy_md_path': md_rel,
        'internal_json_path': str((internal_platform / f'{stem}.json').relative_to(workspace)) if json_payload is not None else None,
        'internal_md_path': str((internal_platform / f'{stem}.md').relative_to(workspace)) if markdown_text is not None else None,
    }
