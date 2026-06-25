"""Governance checks for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.policy.suite_quality_policy import evaluate_suite_quality, evaluate_workspace_quality


def build_self_governance_status(root: Path, suite: str) -> dict[str, Any]:
    """Build self governance status.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = evaluate_workspace_quality(root)
    suite_check = evaluate_suite_quality(root, suite)
    failures = [f'workspace:{item}' for item in workspace['missing']] + [f'suite:{item}' for item in suite_check['missing']]
    warnings = list(workspace['warnings']) + list(suite_check['warnings'])
    return {
        'ok': bool(workspace['ok'] and suite_check['ok']),
        'suite': suite,
        'failures': failures,
        'warnings': warnings,
        'workspace': workspace,
        'suite_check': suite_check,
    }
