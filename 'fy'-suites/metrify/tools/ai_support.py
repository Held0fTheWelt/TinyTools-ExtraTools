"""Ai support for metrify.tools.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json

from .repo_paths import fy_suite_dir, suite_dir


def write_ai_pack(repo_root: Path, summary: dict[str, Any]) -> dict[str, str]:
    """Write ai pack.

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
    # write_ai_pack.
    payload = {
        'kind': 'ai_cost_context',
        'summary': {
            'total_cost_usd': summary.get('total_cost_usd', 0.0),
            'today_cost_usd': summary.get('today_cost_usd', 0.0),
            'last_10_runs_cost_usd': summary.get('last_10_runs_cost_usd', 0.0),
            'top_models': summary.get('top_models', [])[:5],
            'top_suites': summary.get('top_suites', [])[:5],
            'optimization_suggestions': summary.get('optimization_suggestions', [])[:5],
        },
        'recommended_usage': [
            'Use this pack before selecting a model for a new suite wave.',
            'Compare intended model choice against the current top cost drivers.',
            'Record utility_score where possible so future runs can measure cost versus value.',
        ],
    }
    hints = '\n'.join(f'- {item}' for item in summary.get('optimization_suggestions', [])[:5])
    md = (
        '# Metrify AI Context\n\n'
        f"- Total cost (USD): {summary.get('total_cost_usd', 0.0)}\n"
        f"- Today cost (USD): {summary.get('today_cost_usd', 0.0)}\n"
        f"- Last 10 runs cost (USD): {summary.get('last_10_runs_cost_usd', 0.0)}\n\n"
        '## Optimization hints\n' + hints + '\n'
    )
    out1 = suite_dir(repo_root) / 'reports' / 'metrify_ai_context.json'
    out2 = suite_dir(repo_root) / 'reports' / 'metrify_ai_context.md'
    llms = suite_dir(repo_root) / 'reports' / 'llms.txt'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(out1, payload)
    out2.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    out2.write_text(md, encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    llms.write_text(
        'Metrify AI context\n\n'
        '- Start with reports/metrify_cost_report.md\n'
        '- Then inspect reports/metrify_ai_context.md\n'
        '- Use state/latest_summary.json for machine-readable totals and top drivers\n',
        encoding='utf-8',
    )
    fyout1 = fy_suite_dir(repo_root) / 'reports' / 'metrify_ai_context.json'
    fyout2 = fy_suite_dir(repo_root) / 'reports' / 'metrify_ai_context.md'
    fyllms = fy_suite_dir(repo_root) / 'reports' / 'llms.txt'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(fyout1, payload)
    fyout2.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    fyout2.write_text(md, encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    fyllms.write_text(llms.read_text(encoding='utf-8'), encoding='utf-8')
    return {
        'ai_context_json': str(out1.relative_to(repo_root)),
        'ai_context_md': str(out2.relative_to(repo_root)),
        'llms_txt': str(llms.relative_to(repo_root)),
    }
