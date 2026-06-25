"""Cli parser for fy_platform.tools.

"""
from __future__ import annotations

import argparse


def add_platform_shell_parsers(sub, commands) -> None:
    """Add platform shell parsers.

    Args:
        sub: Primary sub used by this step.
        commands: Primary commands used by this step.
    """
    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_an = sub.add_parser('analyze', help='Platform-first analysis entry point.')
    p_an.add_argument('--mode', required=True, help='Platform mode such as contract, quality, docs, security, or structure.')
    p_an.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_an.add_argument('--target-repo', default='', help='Optional outward target repository for analyze modes.')
    p_an.add_argument('--query', default='', help='Optional query hint for targeted analysis.')
    p_an.set_defaults(func=commands['analyze'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_in = sub.add_parser('inspect', help='Platform-first inspect entry point.')
    p_in.add_argument('--mode', required=True, help='Platform mode such as contract, quality, docs, security, or structure.')
    p_in.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_in.add_argument('--query', default='', help='Optional query hint for inspection.')
    p_in.set_defaults(func=commands['inspect'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_ex = sub.add_parser('explain', help='Platform-first explain entry point.')
    p_ex.add_argument('--mode', required=True, help='Platform mode such as contract, docs, or code_docs.')
    p_ex.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_ex.add_argument('--audience', default='developer', help='Audience for explanation output.')
    p_ex.set_defaults(func=commands['explain'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_gen = sub.add_parser('generate', help='Platform-first generation entry point.')
    p_gen.add_argument('--mode', required=True, help='Platform mode such as context_pack or docs.')
    p_gen.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_gen.add_argument('--target-repo', default='', help='Optional outward target repository for generation.')
    p_gen.add_argument('--query', default='', help='Query or seed used to generate the artifact.')
    p_gen.add_argument('--audience', default='developer', help='Audience for generation surfaces that support it.')
    p_gen.set_defaults(func=commands['generate'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_gov = sub.add_parser('govern', help='Platform-first governance entry point.')
    p_gov.add_argument('--mode', required=True, help='Platform mode such as release or production.')
    p_gov.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_gov.set_defaults(func=commands['govern'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_imp = sub.add_parser('import', help='Platform-first import entry point.')
    p_imp.add_argument('--mode', required=True, help='Platform mode such as mvp.')
    p_imp.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_imp.add_argument('--bundle', default='', help='Import bundle path for the selected mode.')
    p_imp.set_defaults(func=commands['import'])

    # Read and normalize the input data before add_platform_shell_parsers branches on or
    # transforms it further.
    p_met = sub.add_parser('metrics', help='Platform-first metrics entry point.')
    p_met.add_argument('--mode', required=True, help='Platform mode such as report or governor_status.')
    p_met.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_met.set_defaults(func=commands['metrics'])


def add_strategy_parsers(sub, commands) -> None:
    """Add strategy profile parsers.

    Args:
        sub: Primary sub used by this step.
        commands: Primary commands used by this step.
    """
    parser = sub.add_parser('strategy', help='Show or update the active Markdown-backed strategy profile.')
    strategy_sub = parser.add_subparsers(dest='strategy_command', required=True)

    p_show = strategy_sub.add_parser('show', help='Print the active strategy profile.')
    p_show.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_show.set_defaults(func=commands['strategy_show'])

    p_set = strategy_sub.add_parser('set', help='Persist a new active strategy profile.')
    p_set.add_argument('profile', choices=['A', 'B', 'C', 'D', 'E'])
    p_set.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_set.set_defaults(func=commands['strategy_set'])


def add_workspace_parsers(sub, commands) -> None:
    """Add workspace parsers.

    Args:
        sub: Primary sub used by this step.
        commands: Primary commands used by this step.
    """
    p_boot = sub.add_parser('bootstrap', help='Generate fy-manifest.yaml with conservative defaults.')
    p_boot.add_argument('--force', action='store_true', help='Overwrite existing manifest.')
    p_boot.add_argument('--project-root', default='', help='Optional explicit project root path.')
    p_boot.set_defaults(func=commands['bootstrap'])

    p_val = sub.add_parser('validate-manifest', help='Validate fy-manifest.yaml shape minimally.')
    p_val.add_argument('--project-root', default='', help='Optional explicit project root path.')
    p_val.set_defaults(func=commands['validate'])

    p_ws = sub.add_parser('workspace-status', help='Write and print an aggregated workspace status site.')
    p_ws.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_ws.set_defaults(func=commands['workspace_status'])

    p_rr = sub.add_parser('release-readiness', help='Write and print aggregated release readiness for the fy workspace.')
    p_rr.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_rr.set_defaults(func=commands['release_readiness'])

    p_pr = sub.add_parser('production-readiness', help='Write and print aggregated production-hardening readiness for the fy workspace.')
    p_pr.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_pr.set_defaults(func=commands['production_readiness'])

    p_cb = sub.add_parser('create-backup', help='Create a managed backup for workspace state and contracts.')
    p_cb.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_cb.add_argument('--reason', default='manual', help='Reason to record in the backup manifest.')
    p_cb.set_defaults(func=commands['create_backup'])

    p_rb = sub.add_parser('rollback-backup', help='Restore a managed backup into the fy workspace.')
    p_rb.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_rb.add_argument('--backup-id', default='', help='Specific backup identifier; defaults to latest.')
    p_rb.set_defaults(func=commands['rollback_backup'])

    p_obs = sub.add_parser('observability-status', help='Print current command/route observability summary.')
    p_obs.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
    p_obs.set_defaults(func=commands['observability_status'])


def add_product_parsers(sub, commands) -> None:
    """Add product parsers.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        sub: Primary sub used by this step.
        commands: Primary commands used by this step.
    """
    for name, help_text, func_key in [
        ('suite-catalog', 'Write and print the full suite catalog for this fy workspace.', 'suite_catalog'),
        ('command-reference', 'Write and print the stable suite command reference.', 'command_reference'),
        ('export-schemas', 'Export JSON-schema-style contract files for shared platform payloads.', 'export_schemas'),
        ('ai-capability-report', 'Write and print the current AI capability matrix for all suites.', 'ai_capability_report'),
        ('doctor', 'Write and print the top-level workspace doctor report.', 'doctor'),
        ('final-release-bundle', 'Write and print the full final release bundle for this fy workspace.', 'final_release_bundle'),
    ]:
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument('--project-root', default='', help='Optional explicit fy workspace path.')
        parser.set_defaults(func=commands[func_key])
