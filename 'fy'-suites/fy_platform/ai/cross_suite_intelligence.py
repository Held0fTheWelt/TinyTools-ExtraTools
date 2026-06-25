"""Cross suite intelligence for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.workspace import workspace_root

RELATED_SUITES = {
    'contractify': ['testify', 'documentify', 'docify', 'templatify', 'usabilify', 'securify'],
    'testify': ['contractify', 'documentify', 'docify', 'despaghettify', 'securify'],
    'documentify': ['docify', 'templatify', 'usabilify', 'contractify', 'securify'],
    'docify': ['documentify', 'contractify', 'despaghettify', 'securify'],
    'despaghettify': ['docify', 'testify', 'documentify', 'securify'],
    'templatify': ['documentify', 'usabilify', 'contractify', 'securify'],
    'usabilify': ['templatify', 'documentify', 'contractify', 'securify'],
    'securify': ['contractify', 'testify', 'documentify', 'docify', 'usabilify', 'observifyfy', 'metrify'],
    'observifyfy': ['contractify', 'documentify', 'testify', 'docify', 'templatify', 'usabilify', 'securify', 'mvpify', 'metrify'],
    'mvpify': ['contractify', 'despaghettify', 'testify', 'documentify', 'templatify', 'usabilify', 'securify', 'observifyfy', 'metrify'],
    'metrify': ['observifyfy', 'contractify', 'testify', 'documentify', 'docify', 'mvpify'],
}

RELATION_EDGES = {
    'contractify': [('testify', 'requires_review_from'), ('documentify', 'informs'), ('docify', 'projects_to'), ('securify', 'conflicts_with')],
    'testify': [('contractify', 'validates'), ('despaghettify', 'improves')],
    'documentify': [('templatify', 'depends_on'), ('usabilify', 'informs')],
    'mvpify': [('contractify', 'informs'), ('observifyfy', 'informs'), ('metrify', 'informs')],
}


def _status_json_path(root: Path, suite: str) -> Path:
    """Status json path.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return root / suite / 'reports' / 'status' / 'most_recent_next_steps.json'


def _load_status(root: Path, suite: str) -> dict[str, Any] | None:
    """Load status.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.

    Returns:
        dict[str, Any] | None:
            Structured payload describing the outcome of the
            operation.
    """
    path = _status_json_path(root, suite)
    # Branch on not path.is_file() so _load_status only continues along the matching
    # state path.
    if not path.is_file():
        return None
    # Protect the critical _load_status work so failures can be turned into a controlled
    # result or cleanup path.
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def _suite_matches_query(suite: str, query: str) -> bool:
    """Suite matches query.

    Args:
        suite: Primary suite used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    query_l = (query or '').lower()
    return bool(query_l and suite.lower() in query_l)


def _relation_reason(source_suite: str, target_suite: str) -> str:
    """Relation reason.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source_suite: Primary source suite used by this step.
        target_suite: Primary target suite used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    for candidate, relation in RELATION_EDGES.get(source_suite, []):
        if candidate == target_suite:
            return relation
    return f'{source_suite}_related_signal'


def collect_cross_suite_signals(root: Path, suite: str, query: str | None = None, limit: int = 5) -> dict[str, Any]:
    """Collect cross suite signals.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.
        query: Free-text input that shapes this operation.
        limit: Primary limit used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    root = workspace_root(root)
    registry = EvidenceRegistry(root)
    related = RELATED_SUITES.get(suite, [])
    rows: list[dict[str, Any]] = []
    for rel in related:
        latest = registry.latest_run(rel)
        status = _load_status(root, rel)
        if not latest and not status:
            continue
        score = 0
        if latest and latest.get('status') == 'ok':
            score += 2
        if status and status.get('ok'):
            score += 2
        if _suite_matches_query(rel, query or ''):
            score += 3
        if status and status.get('next_steps'):
            score += 1
        rows.append({'suite': rel, 'score': score, 'latest_run': latest, 'status_summary': (status or {}).get('summary', ''), 'next_steps': list((status or {}).get('next_steps', []))[:3], 'status_ok': bool((status or {}).get('ok', False)), 'relation_reason': _relation_reason(suite, rel)})
    rows.sort(key=lambda item: (item['score'], item['suite']), reverse=True)
    top = rows[:limit]
    return {'suite': suite, 'related_suites': related, 'relation_edges': RELATION_EDGES.get(suite, []), 'signal_count': len(top), 'signals': top, 'summary': _render_summary(suite, top)}


def _render_summary(suite: str, signals: list[dict[str, Any]]) -> str:
    """Render summary.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        suite: Primary suite used by this step.
        signals: Primary signals used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if not signals:
        return f'No recent cross-suite signals are available for {suite}.'
    top = signals[0]
    return f"The strongest cross-suite signal for {suite} currently comes from {top['suite']} via {top['relation_reason']}. Use it to connect the latest result with nearby suite work instead of treating the suite in isolation."
