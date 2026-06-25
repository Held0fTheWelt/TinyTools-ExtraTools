"""Release readiness data for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.policy.suite_quality_policy import CORE_SUITES, OPTIONAL_SUITES, evaluate_suite_quality, evaluate_workspace_quality
from fy_platform.ai.workspace import utc_now, workspace_root

STATUS_REL_JSON = Path('reports/status/most_recent_next_steps.json')
STATUS_REL_MD = Path('reports/status/MOST_RECENT_NEXT_STEPS.md')


def load_status_json(path: Path) -> dict[str, Any] | None:
    """Load status json.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any] | None:
            Structured payload describing the outcome of the
            operation.
    """
    # Branch on not path.is_file() so load_status_json only continues along the matching
    # state path.
    if not path.is_file():
        return None
    # Protect the critical load_status_json work so failures can be turned into a
    # controlled result or cleanup path.
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def suite_release_readiness(workspace: Path, suite: str) -> dict[str, Any]:
    """Suite release readiness.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace: Primary workspace used by this step.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(workspace)
    registry = EvidenceRegistry(workspace)
    latest = registry.latest_run(suite)
    suite_check = evaluate_suite_quality(workspace, suite)
    status = load_status_json(workspace / suite / STATUS_REL_JSON)
    has_run = latest is not None
    latest_ok = bool(latest and latest.get('status') == 'ok')
    next_steps = list((status or {}).get('next_steps', []))[:8]
    warnings = list((status or {}).get('warnings', []))
    if suite_check['warnings']:
        warnings.extend(item for item in suite_check['warnings'] if item not in warnings)
    ready = bool(suite_check['ok'] and has_run and latest_ok)
    blocking_reasons: list[str] = []
    if not suite_check['ok']:
        blocking_reasons.extend([f'missing:{item}' for item in suite_check['missing']])
    if not has_run:
        blocking_reasons.append('no_successful_run_recorded')
    elif not latest_ok:
        blocking_reasons.append(f"latest_run_status:{latest.get('status')}")
    return {
        'suite': suite,
        'ready': ready,
        'has_run': has_run,
        'latest_run': latest,
        'status_page_json': str((workspace / suite / STATUS_REL_JSON).relative_to(workspace)) if (workspace / suite / STATUS_REL_JSON).is_file() else None,
        'status_page_md': str((workspace / suite / STATUS_REL_MD).relative_to(workspace)) if (workspace / suite / STATUS_REL_MD).is_file() else None,
        'next_steps': next_steps,
        'warnings': warnings,
        'blocking_reasons': blocking_reasons,
        'suite_check': suite_check,
    }


def workspace_release_readiness(workspace: Path, suites: list[str] | None = None) -> dict[str, Any]:
    """Workspace release readiness.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace: Primary workspace used by this step.
        suites: Primary suites used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(workspace)
    workspace_check = evaluate_workspace_quality(workspace)
    if suites is None:
        suites = sorted({*CORE_SUITES, *OPTIONAL_SUITES, *[p.name for p in workspace.iterdir() if p.is_dir() and (p / 'adapter').is_dir()]})
    suite_rows = [suite_release_readiness(workspace, suite) for suite in suites if (workspace / suite).is_dir()]
    core_ready = [row['suite'] for row in suite_rows if row['suite'] in CORE_SUITES and row['ready']]
    core_missing = [row['suite'] for row in suite_rows if row['suite'] in CORE_SUITES and not row['ready']]
    optional_ready = [row['suite'] for row in suite_rows if row['suite'] in OPTIONAL_SUITES and row['ready']]
    optional_missing = [row['suite'] for row in suite_rows if row['suite'] in OPTIONAL_SUITES and not row['ready']]
    ok = bool(workspace_check['ok'] and not core_missing)
    return {
        'schema_version': 'fy.workspace-release-readiness.v1',
        'generated_at': utc_now(),
        'workspace_root': str(workspace),
        'ok': ok,
        'workspace_check': workspace_check,
        'core_ready_suites': core_ready,
        'core_blocked_suites': core_missing,
        'optional_ready_suites': optional_ready,
        'optional_blocked_suites': optional_missing,
        'suites': suite_rows,
    }
