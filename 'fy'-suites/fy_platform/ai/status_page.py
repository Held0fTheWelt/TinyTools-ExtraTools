"""Status page for fy_platform.ai.

"""
from __future__ import annotations

from typing import Any

from fy_platform.ai.status_page_analysis import decision_summary, derive_next_steps
from fy_platform.ai.status_page_rendering import render_status_markdown, write_status_page


def build_status_payload(suite: str, command: str, payload: dict[str, Any], latest_run: dict[str, Any] | None = None, governance: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build status payload.

    Args:
        suite: Primary suite used by this step.
        command: Named command for this operation.
        payload: Structured data carried through this workflow.
        latest_run: Primary latest run used by this step.
        governance: Primary governance used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    summary, uncertainty = decision_summary(payload)
    return {
        'suite': suite,
        'command': command,
        'ok': bool(payload.get('ok', False)),
        'summary': payload.get('summary', 'No summary is available yet.'),
        'decision_summary': summary,
        'latest_run': latest_run,
        'next_steps': list(payload.get('next_steps', [])) or derive_next_steps(suite, command, payload),
        'key_signals': {k: payload[k] for k in ['finding_count', 'hit_count', 'drift_count', 'local_spike_count', 'template_count', 'latest_artifact_count'] if k in payload},
        'warnings': list(payload.get('warnings', [])),
        'active_strategy_profile': payload.get('active_strategy_profile') or ((latest_run or {}).get('run_metadata') or {}).get('active_strategy_profile') or {},
        'cross_suite': payload.get('cross_suite') or {},
        'governance': governance,
        'uncertainty': list(payload.get('uncertainty', [])) + uncertainty,
    }


__all__ = ['build_status_payload', 'render_status_markdown', 'write_status_page']
