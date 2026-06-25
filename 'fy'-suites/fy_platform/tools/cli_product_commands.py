"""Cli product commands for fy_platform.tools.

"""
from __future__ import annotations

import argparse
import json

from fy_platform.ai.final_product import (
    ai_capability_payload,
    command_reference_payload,
    doctor_payload,
    export_contract_schemas,
    final_release_bundle,
    render_ai_capability_markdown,
    render_command_reference_markdown,
    render_doctor_markdown,
    render_suite_catalog_markdown,
    suite_catalog_payload,
)
from fy_platform.ai.workspace import write_platform_doc_artifacts, write_text
from fy_platform.tools.cli_workspace_commands import resolve_repo


def cmd_suite_catalog(args: argparse.Namespace) -> int:
    """Cmd suite catalog.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # cmd_suite_catalog.
    repo = resolve_repo(args.project_root)
    payload = suite_catalog_payload(repo)
    write_platform_doc_artifacts(repo, stem='suite_catalog', json_payload=payload, markdown_text=render_suite_catalog_markdown(payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_command_reference(args: argparse.Namespace) -> int:
    """Cmd command reference.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = command_reference_payload(repo)
    write_platform_doc_artifacts(repo, stem='command_reference', json_payload=payload, markdown_text=render_command_reference_markdown(payload))
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(repo / 'docs' / 'platform' / 'SUITE_COMMAND_REFERENCE.md', render_command_reference_markdown(payload))
    legacy = repo / "'fy'-suites" / 'docs' / 'platform' / 'SUITE_COMMAND_REFERENCE.md'
    if legacy.parent.exists():
        write_text(legacy, render_command_reference_markdown(payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_export_schemas(args: argparse.Namespace) -> int:
    """Cmd export schemas.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    print(json.dumps(export_contract_schemas(repo), indent=2, ensure_ascii=False))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Cmd doctor.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = doctor_payload(repo)
    write_platform_doc_artifacts(repo, stem='doctor', json_payload=payload, markdown_text=render_doctor_markdown(payload))
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(repo / 'docs' / 'platform' / 'DOCTOR.md', render_doctor_markdown(payload))
    legacy = repo / "'fy'-suites" / 'docs' / 'platform' / 'DOCTOR.md'
    if legacy.parent.exists():
        write_text(legacy, render_doctor_markdown(payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get('ok') else 5


def cmd_final_release_bundle(args: argparse.Namespace) -> int:
    """Cmd final release bundle.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = final_release_bundle(repo)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get('workspace_release', {}).get('ok') else 6


def cmd_ai_capability_report(args: argparse.Namespace) -> int:
    """Cmd ai capability report.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = ai_capability_payload(repo)
    paths = write_platform_doc_artifacts(repo, stem='ai_capability_matrix', json_payload=payload, markdown_text=render_ai_capability_markdown(payload))
    print(json.dumps({'ok': True, **paths}, indent=2, ensure_ascii=False))
    return 0
