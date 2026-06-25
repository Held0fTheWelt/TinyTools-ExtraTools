"""Fy platform bootstrap and workspace governance CLI."""
from __future__ import annotations

import argparse
from typing import Sequence

from fy_platform.surfaces.public_cli import (
    cmd_analyze,
    cmd_explain_mode,
    cmd_generate,
    cmd_govern,
    cmd_import_mode,
    cmd_inspect_mode,
    cmd_metrics_mode,
)
from fy_platform.tools.cli_parser import add_platform_shell_parsers, add_product_parsers, add_strategy_parsers, add_workspace_parsers
from fy_platform.tools.cli_product_commands import (
    cmd_ai_capability_report,
    cmd_command_reference,
    cmd_doctor,
    cmd_export_schemas,
    cmd_final_release_bundle,
    cmd_suite_catalog,
)
from fy_platform.tools.cli_strategy_commands import cmd_strategy_set, cmd_strategy_show
from fy_platform.tools.cli_workspace_commands import (
    build_manifest_payload,
    cmd_bootstrap,
    cmd_create_backup,
    cmd_observability_status,
    cmd_production_readiness,
    cmd_release_readiness,
    cmd_rollback_backup,
    cmd_validate,
    cmd_workspace_status,
    detect_roots,
    resolve_repo,
)

__all__ = [
    'build_manifest_payload',
    'cmd_ai_capability_report',
    'cmd_analyze',
    'cmd_bootstrap',
    'cmd_command_reference',
    'cmd_create_backup',
    'cmd_doctor',
    'cmd_explain_mode',
    'cmd_export_schemas',
    'cmd_final_release_bundle',
    'cmd_generate',
    'cmd_govern',
    'cmd_import_mode',
    'cmd_inspect_mode',
    'cmd_metrics_mode',
    'cmd_observability_status',
    'cmd_production_readiness',
    'cmd_release_readiness',
    'cmd_strategy_set',
    'cmd_strategy_show',
    'cmd_rollback_backup',
    'cmd_suite_catalog',
    'cmd_validate',
    'cmd_workspace_status',
    'detect_roots',
    'main',
    'resolve_repo',
]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Read and normalize the input data before main branches on or transforms it
    # further.
    parser = argparse.ArgumentParser(description='Fy platform utilities.')
    sub = parser.add_subparsers(dest='command', required=True)
    add_platform_shell_parsers(sub, {
        'analyze': cmd_analyze,
        'inspect': cmd_inspect_mode,
        'explain': cmd_explain_mode,
        'generate': cmd_generate,
        'govern': cmd_govern,
        'import': cmd_import_mode,
        'metrics': cmd_metrics_mode,
    })
    add_strategy_parsers(sub, {
        'strategy_show': cmd_strategy_show,
        'strategy_set': cmd_strategy_set,
    })
    add_workspace_parsers(sub, {
        'bootstrap': cmd_bootstrap,
        'validate': cmd_validate,
        'workspace_status': cmd_workspace_status,
        'release_readiness': cmd_release_readiness,
        'production_readiness': cmd_production_readiness,
        'create_backup': cmd_create_backup,
        'rollback_backup': cmd_rollback_backup,
        'observability_status': cmd_observability_status,
    })
    add_product_parsers(sub, {
        'suite_catalog': cmd_suite_catalog,
        'command_reference': cmd_command_reference,
        'export_schemas': cmd_export_schemas,
        'ai_capability_report': cmd_ai_capability_report,
        'doctor': cmd_doctor,
        'final_release_bundle': cmd_final_release_bundle,
    })
    # Read and normalize the input data before main branches on or transforms it
    # further.
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))
