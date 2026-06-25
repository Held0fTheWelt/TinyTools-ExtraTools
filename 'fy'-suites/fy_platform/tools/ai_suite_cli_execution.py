"""Ai suite cli execution for fy_platform.tools.

"""
from __future__ import annotations

from fy_platform.ai.graph_recipes import run_audit_recipe, run_context_pack_recipe, run_inspect_recipe, run_triage_recipe


def _recipe_payload(recipe) -> dict:
    """Recipe payload.

    Args:
        recipe: Primary recipe used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    return {**recipe.output, 'recipe': recipe.recipe, 'steps': [step.__dict__ for step in recipe.steps]}


def execute_command(adapter, args) -> dict:
    """Execute command.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        args: Command-line arguments to parse for this invocation.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    # Branch on args.command == 'init' so execute_command only continues along the
    # matching state path.
    if args.command == 'init':
        return adapter.init(args.target_repo or None)
    # Branch on args.command == 'inspect' so execute_command only continues along the
    # matching state path.
    if args.command == 'inspect':
        return _recipe_payload(run_inspect_recipe(adapter, args.query or None))
    # Branch on args.command == 'audit' so execute_command only continues along the
    # matching state path.
    if args.command == 'audit':
        return _recipe_payload(run_audit_recipe(adapter, args.target_repo))
    # Branch on args.command == 'explain' so execute_command only continues along the
    # matching state path.
    if args.command == 'explain':
        return adapter.explain(args.audience)
    # Branch on args.command == 'prepare-context-pack' so execute_command only continues
    # along the matching state path.
    if args.command == 'prepare-context-pack':
        return _recipe_payload(run_context_pack_recipe(adapter, args.query, args.audience))
    # Branch on args.command == 'compare-runs' so execute_command only continues along
    # the matching state path.
    if args.command == 'compare-runs':
        return adapter.compare_runs(args.left_run_id, args.right_run_id)
    # Branch on args.command == 'clean' so execute_command only continues along the
    # matching state path.
    if args.command == 'clean':
        return adapter.clean(args.mode)
    # Branch on args.command == 'reset' so execute_command only continues along the
    # matching state path.
    if args.command == 'reset':
        return adapter.reset(args.mode)
    # Branch on args.command == 'triage' so execute_command only continues along the
    # matching state path.
    if args.command == 'triage':
        return _recipe_payload(run_triage_recipe(adapter, args.query or None))
    # Branch on args.command == 'prepare-fix' so execute_command only continues along
    # the matching state path.
    if args.command == 'prepare-fix':
        return adapter.prepare_fix(args.finding_id)
    # Branch on args.command == 'consolidate' so execute_command only continues along
    # the matching state path.
    if args.command == 'consolidate':
        return adapter.consolidate(args.target_repo, apply_safe=args.apply_safe, instruction=args.instruction or None)
    # Branch on args.command == 'import' so execute_command only continues along the
    # matching state path.
    if args.command == 'import':
        return adapter.import_bundle(args.bundle, legacy=False)
    # Branch on args.command == 'legacy-import' so execute_command only continues along
    # the matching state path.
    if args.command == 'legacy-import':
        return adapter.import_bundle(args.bundle, legacy=True)
    # Branch on args.command == 'self-audit' so execute_command only continues along the
    # matching state path.
    if args.command == 'self-audit':
        return adapter.self_audit()
    # Branch on args.command == 'release-readiness' so execute_command only continues
    # along the matching state path.
    if args.command == 'release-readiness':
        return adapter.release_readiness()
    # Branch on args.command == 'production-readiness' so execute_command only continues
    # along the matching state path.
    if args.command == 'production-readiness':
        return adapter.production_readiness()
    custom_name = args.command.replace('-', '_')
    if hasattr(adapter, custom_name):
        handler = getattr(adapter, custom_name)
        if args.command in {'diagnose', 'readiness-case', 'blocker-graph', 'assemble', 'closure-pack', 'residue-report', 'bundle'}:
            return handler(args.target_repo)
    raise ValueError('unsupported command')
