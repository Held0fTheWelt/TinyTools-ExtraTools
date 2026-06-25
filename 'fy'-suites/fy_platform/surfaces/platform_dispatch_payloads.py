"""Platform dispatch payloads for fy_platform.surfaces.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.production_readiness import workspace_production_readiness, write_workspace_production_site
from fy_platform.ai.release_readiness import workspace_release_readiness, write_workspace_release_site
from fy_platform.runtime.packaging_preparation import write_packaging_preparation_bundle
from fy_platform.surfaces.alias_map import write_surface_alias_artifacts
from fy_platform.surfaces.lens_registry import ADAPTERS


def run_adapter(spec, workspace: Path, args) -> tuple[dict, str]:
    """Run adapter.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        spec: Primary spec used by this step.
        workspace: Primary workspace used by this step.
        args: Command-line arguments to parse for this invocation.

    Returns:
        tuple[dict, str]:
            Structured payload describing the outcome of the
            operation.
    """
    adapter_cls = ADAPTERS[spec.suite]
    adapter = adapter_cls(root=workspace)
    command = spec.adapter_command
    # Branch on command == 'audit' so run_adapter only continues along the matching
    # state path.
    if command == 'audit':
        target_repo = getattr(args, 'target_repo', '') or str(workspace)
        return adapter.audit(target_repo), adapter.suite
    # Branch on command == 'inspect' so run_adapter only continues along the matching
    # state path.
    if command == 'inspect':
        return adapter.inspect(args.query or None), adapter.suite
    # Branch on command == 'explain' so run_adapter only continues along the matching
    # state path.
    if command == 'explain':
        return adapter.explain(getattr(args, 'audience', 'developer')), adapter.suite
    # Branch on command == 'prepare-context-pack' so run_adapter only continues along
    # the matching state path.
    if command == 'prepare-context-pack':
        return adapter.prepare_context_pack(args.query or spec.mode_name, getattr(args, 'audience', 'developer')), adapter.suite
    # Branch on command == 'import' so run_adapter only continues along the matching
    # state path.
    if command == 'import':
        return adapter.import_bundle(args.bundle, legacy=False), adapter.suite
    raise RuntimeError(f'unsupported adapter command: {command}')


def govern_payload(workspace: Path, mode_name: str) -> dict:
    """Govern payload.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace: Primary workspace used by this step.
        mode_name: Primary mode name used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    if mode_name == 'release':
        payload = workspace_release_readiness(workspace)
        payload.update(write_workspace_release_site(workspace, payload))
        return payload
    if mode_name == 'production':
        payload = workspace_production_readiness(workspace)
        payload.update(write_workspace_production_site(workspace, payload))
        return payload
    raise RuntimeError(f'unsupported govern mode: {mode_name}')


def special_generate_payload(workspace: Path, mode_name: str) -> tuple[dict, str] | None:
    """Special generate payload.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace: Primary workspace used by this step.
        mode_name: Primary mode name used by this step.

    Returns:
        tuple[dict, str] | None:
            Structured payload describing the outcome of the
            operation.
    """
    if mode_name == 'surface_aliases':
        return write_surface_alias_artifacts(workspace), 'fy-platform'
    if mode_name == 'packaging_prep':
        return write_packaging_preparation_bundle(workspace), 'fy-platform'
    return None
