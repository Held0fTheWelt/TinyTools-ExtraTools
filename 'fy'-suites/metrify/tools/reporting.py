"""Reporting for metrify.tools.

"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import write_json

from .ledger import read_events
from .repo_paths import fy_suite_dir, suite_dir


def _today_utc() -> str:
    """Today utc.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return datetime.now(timezone.utc).date().isoformat()


def _sum_cost(events: list[dict[str, Any]]) -> float:
    """Sum cost.

    Args:
        events: Primary events used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    return round(sum(float(e.get('cost_usd', 0.0) or 0.0) for e in events), 8)


def _sum_tokens(events: list[dict[str, Any]], key: str) -> int:
    """Sum tokens.

    Args:
        events: Primary events used by this step.
        key: Primary key used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    return int(sum(int(e.get(key, 0) or 0) for e in events))


def _group_by_run(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group by run.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        events: Primary events used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # Process event one item at a time so _group_by_run applies the same rule across the
    # full collection.
    for event in events:
        grouped[str(event.get('run_id', 'unknown-run'))].append(event)
    runs: list[dict[str, Any]] = []
    # Process (run_id, items) one item at a time so _group_by_run applies the same rule
    # across the full collection.
    for run_id, items in grouped.items():
        items.sort(key=lambda e: e.get('timestamp_utc', ''))
        utility_values = [float(i.get('utility_score')) for i in items if i.get('utility_score') is not None]
        runs.append({
            'run_id': run_id,
            'suite': items[-1].get('suite', 'unknown'),
            'event_count': len(items),
            'latest_timestamp_utc': items[-1].get('timestamp_utc'),
            'cost_usd': _sum_cost(items),
            'input_tokens': _sum_tokens(items, 'input_tokens'),
            'cached_input_tokens': _sum_tokens(items, 'cached_input_tokens'),
            'output_tokens': _sum_tokens(items, 'output_tokens'),
            'models': sorted({str(i.get('model', 'unknown')) for i in items}),
            'utility_score_avg': round(sum(utility_values) / len(utility_values), 4) if utility_values else None,
            'resolved_findings': sum(int(i.get('resolved_findings', 0) or 0) for i in items),
            'technique_tags': sorted({tag for i in items for tag in i.get('technique_tags', [])}),
        })
    runs.sort(key=lambda r: r['latest_timestamp_utc'] or '', reverse=True)
    return runs


def _top_breakdown(events: list[dict[str, Any]], field: str, limit: int = 5) -> list[dict[str, Any]]:
    """Top breakdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        events: Primary events used by this step.
        field: Primary field used by this step.
        limit: Primary limit used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        values = event.get(field)
        if isinstance(values, list):
            vals = values or ['untagged']
        else:
            vals = [str(values or 'unknown')]
        for value in vals:
            grouped[str(value)].append(event)
    rows = []
    for key, items in grouped.items():
        rows.append({'key': key, 'cost_usd': _sum_cost(items), 'event_count': len(items), 'output_tokens': _sum_tokens(items, 'output_tokens')})
    rows.sort(key=lambda r: (r['cost_usd'], r['output_tokens'], r['event_count']), reverse=True)
    return rows[:limit]


def _optimization_suggestions(events: list[dict[str, Any]], runs: list[dict[str, Any]]) -> list[str]:
    """Optimization suggestions.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        events: Primary events used by this step.
        runs: Primary runs used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[str] = []
    if not events:
        return ['No usage events yet. Instrument suites or ingest usage logs first.']
    total_input = _sum_tokens(events, 'input_tokens')
    total_cached = _sum_tokens(events, 'cached_input_tokens')
    total_output = _sum_tokens(events, 'output_tokens')
    if total_input > 0 and total_cached == 0:
        out.append('Cached-input usage is zero. Reused prompts or stable context blocks may reduce input spend.')
    if total_output > total_input * 1.5:
        out.append('Output tokens dominate input tokens. Tighter output schemas or shorter completion targets may cut spend.')
    by_model = _top_breakdown(events, 'model', limit=3)
    if by_model:
        top = by_model[0]
        if top['key'] == 'gpt-5.4':
            out.append('GPT-5.4 is currently the top cost driver. Review whether some runs can move to GPT-5.4-mini or nano.')
        if top['key'] == 'gpt-5.4-pro':
            out.append('GPT-5.4-pro is the top cost driver. Reserve it for only the highest-value professional reasoning steps.')
    low_utility_high_cost = [r for r in runs if (r.get('utility_score_avg') or 0.0) < 0.5 and r['cost_usd'] > 0.05]
    if low_utility_high_cost:
        out.append('Some recent runs have low recorded utility relative to cost. Re-check prompting, orchestration order, or whether a smaller model is enough.')
    if not out:
        out.append('No strong optimization red flags detected from the current ledger sample.')
    return out


def build_summary(ledger_path: Path) -> dict[str, Any]:
    """Build summary.

    Args:
        ledger_path: Filesystem path to the file or directory being
            processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    events = read_events(ledger_path)
    events.sort(key=lambda e: e.get('timestamp_utc', ''))
    runs = _group_by_run(events)
    today = _today_utc()
    today_events = [e for e in events if str(e.get('timestamp_utc', '')).startswith(today)]
    last_run = runs[0] if runs else None
    last_10_runs = runs[:10]
    summary = {
        'ledger_path': str(ledger_path),
        'event_count': len(events),
        'run_count': len(runs),
        'last_run': last_run,
        'last_10_runs_cost_usd': round(sum(float(r['cost_usd']) for r in last_10_runs), 8),
        'today_cost_usd': _sum_cost(today_events),
        'total_cost_usd': _sum_cost(events),
        'total_input_tokens': _sum_tokens(events, 'input_tokens'),
        'total_cached_input_tokens': _sum_tokens(events, 'cached_input_tokens'),
        'total_output_tokens': _sum_tokens(events, 'output_tokens'),
        'top_models': _top_breakdown(events, 'model'),
        'top_suites': _top_breakdown(events, 'suite'),
        'top_techniques': _top_breakdown(events, 'technique_tags'),
        'recent_runs': last_10_runs,
        'optimization_suggestions': _optimization_suggestions(events, runs),
    }
    summary['avg_cost_per_run_usd'] = round(summary['total_cost_usd'] / max(1, len(runs)), 8) if runs else 0.0
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    """Render markdown.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        summary: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '# Metrify Cost Report',
        '',
        f"- Events: {summary.get('event_count', 0)}",
        f"- Runs: {summary.get('run_count', 0)}",
        f"- Last run cost (USD): {((summary.get('last_run') or {}).get('cost_usd', 0.0))}",
        f"- Last 10 runs cost (USD): {summary.get('last_10_runs_cost_usd', 0.0)}",
        f"- Today cost (USD): {summary.get('today_cost_usd', 0.0)}",
        f"- Total cost (USD): {summary.get('total_cost_usd', 0.0)}",
        '',
        '## Biggest cost drivers by model',
    ]
    for row in summary.get('top_models', []):
        lines.append(f"- {row['key']}: ${row['cost_usd']:.6f} across {row['event_count']} events")
    lines.extend(['', '## Biggest cost drivers by suite'])
    for row in summary.get('top_suites', []):
        lines.append(f"- {row['key']}: ${row['cost_usd']:.6f} across {row['event_count']} events")
    lines.extend(['', '## Optimization suggestions'])
    for item in summary.get('optimization_suggestions', []):
        lines.append(f'- {item}')
    return '\n'.join(lines) + '\n'


def write_report_bundle(repo_root: Path, summary: dict[str, Any]) -> dict[str, str]:
    """Write report bundle.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        summary: Structured data carried through this workflow.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    hub = suite_dir(repo_root)
    fyhub = fy_suite_dir(repo_root)
    report_json = hub / 'reports' / 'metrify_cost_report.json'
    report_md = hub / 'reports' / 'metrify_cost_report.md'
    state_json = hub / 'state' / 'latest_summary.json'
    csv_path = hub / 'reports' / 'metrify_recent_runs.csv'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(report_json, summary)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    report_md.write_text(render_markdown(summary), encoding='utf-8')
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(state_json, summary)
    fy_report_json = fyhub / 'reports' / 'metrify_cost_report.json'
    fy_report_md = fyhub / 'reports' / 'metrify_cost_report.md'
    fy_state = fyhub / 'state' / 'latest_summary.json'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(fy_report_json, summary)
    fy_report_md.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    fy_report_md.write_text(render_markdown(summary), encoding='utf-8')
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(fy_state, summary)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['run_id', 'suite', 'cost_usd', 'event_count', 'latest_timestamp_utc', 'models'])
        writer.writeheader()
        for row in summary.get('recent_runs', []):
            writer.writerow({
                'run_id': row.get('run_id', ''),
                'suite': row.get('suite', ''),
                'cost_usd': row.get('cost_usd', 0.0),
                'event_count': row.get('event_count', 0),
                'latest_timestamp_utc': row.get('latest_timestamp_utc', ''),
                'models': ','.join(row.get('models', [])),
            })
    return {
        'report_json': str(report_json.relative_to(repo_root)),
        'report_md': str(report_md.relative_to(repo_root)),
        'state_json': str(state_json.relative_to(repo_root)),
        'csv_path': str(csv_path.relative_to(repo_root)),
    }
