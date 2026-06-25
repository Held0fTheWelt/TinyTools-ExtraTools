"""Observify bridge for metrify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json

from .repo_paths import fy_suite_dir


def write_observify_summary(repo_root: Path, summary: dict[str, Any]) -> dict[str, str]:
    """Write observify summary.

    This callable writes or records artifacts as part of its workflow.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        summary: Structured data carried through this workflow.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # write_observify_summary.
    payload = {
        'suite': 'metrify',
        'metric_kind': 'ai_cost_observability',
        'total_cost_usd': summary.get('total_cost_usd', 0.0),
        'today_cost_usd': summary.get('today_cost_usd', 0.0),
        'last_10_runs_cost_usd': summary.get('last_10_runs_cost_usd', 0.0),
        'top_models': summary.get('top_models', [])[:3],
        'top_suites': summary.get('top_suites', [])[:3],
        'optimization_suggestions': summary.get('optimization_suggestions', [])[:5],
    }
    out = repo_root / '.fydata' / 'bindings' / 'metrify.json'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(out, payload)
    obs = repo_root / "'fy'-suites" / 'observifyfy' / 'reports' / 'observifyfy_metrify_summary.json'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(obs, payload)
    fyobs = fy_suite_dir(repo_root) / 'reports' / 'metrify_observify_summary.json'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(fyobs, payload)
    return {
        'binding_json': str(out.relative_to(repo_root)),
        'observify_summary_json': str(obs.relative_to(repo_root)),
    }
