"""Readiness facade for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.production_readiness import workspace_production_readiness
from fy_platform.ai.release_readiness import suite_release_readiness


def build_release_readiness(root: Path, suite: str) -> dict[str, Any]:
    """Build release readiness.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # build_release_readiness.
    payload = suite_release_readiness(root, suite)
    payload.update({
        'ok': payload['ready'],
        'summary': 'Release readiness tells you if this suite is ready to participate in an MVP release from the current workspace state.',
    })
    return payload


def build_production_readiness(root: Path, suite: str) -> dict[str, Any]:
    """Build production readiness.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace_payload = workspace_production_readiness(root)
    suite_payload = suite_release_readiness(root, suite)
    return {
        'ok': bool(workspace_payload.get('ok') and suite_payload.get('ready')),
        'suite': suite,
        'summary': 'Production readiness is stricter than MVP release readiness. It checks persistence, compatibility, recovery, observability, security, and release-management evidence.',
        'workspace_production': {
            'ok': workspace_payload.get('ok'),
            'workspace_production_md_path': workspace_payload.get('workspace_production_md_path'),
            'top_next_steps': workspace_payload.get('top_next_steps', []),
        },
        'suite_release': suite_payload,
        'warnings': list(suite_payload.get('warnings', [])),
    }
