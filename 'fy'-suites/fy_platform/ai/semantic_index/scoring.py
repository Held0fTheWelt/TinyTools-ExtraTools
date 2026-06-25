"""Scoring for fy_platform.ai.semantic_index.

"""
from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-/]{2,}")


def tokens(text: str) -> list[str]:
    """Tokens the requested operation.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    return [t.lower() for t in TOKEN_RE.findall(text)]


def lexical_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    """Lexical score.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        query_tokens: Primary query tokens used by this step.
        doc_tokens: Primary doc tokens used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    # Branch on not query_tokens or not doc_tokens so lexical_score only continues along
    # the matching state path.
    if not query_tokens or not doc_tokens:
        return 0.0
    q = Counter(query_tokens)
    d = Counter(doc_tokens)
    inter = sum(min(q[t], d.get(t, 0)) for t in q)
    return inter / max(len(query_tokens), 1)


def semantic_score(q: Counter, d: Counter) -> float:
    """Semantic score.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        q: Primary q used by this step.
        d: Primary d used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    if not q or not d:
        return 0.0
    dot = sum(q[k] * d.get(k, 0) for k in q)
    nq = math.sqrt(sum(v * v for v in q.values()))
    nd = math.sqrt(sum(v * v for v in d.values()))
    if nq == 0 or nd == 0:
        return 0.0
    return dot / (nq * nd)


def scope_score(scope: str) -> float:
    """Scope score.

    Args:
        scope: Primary scope used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    return {'target': 1.0, 'suite': 0.8, 'workspace': 0.7}.get(scope or '', 0.5)


def suite_affinity_score(query_tokens: list[str], suite: str, source_path: str) -> float:
    """Suite affinity score.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        query_tokens: Primary query tokens used by this step.
        suite: Primary suite used by this step.
        source_path: Filesystem path to the file or directory being
            processed.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    token_set = set(query_tokens)
    score = 0.0
    if suite.lower() in token_set:
        score += 1.0
    path_bits = {part.lower() for part in re.split(r'[^A-Za-z0-9]+', source_path) if part}
    overlap = token_set & path_bits
    if overlap:
        score += min(0.8, 0.2 * len(overlap))
    return min(score, 1.0)


def recency_score(rowid: int, newest_rowid: int) -> float:
    """Recency score.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        rowid: Primary rowid used by this step.
        newest_rowid: Primary newest rowid used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    if newest_rowid <= 0:
        return 0.0
    return max(0.1, rowid / newest_rowid)


def passes_noise_gate(lexical: float, semantic: float, matched_terms: list[str]) -> bool:
    """Passes noise gate.

    Args:
        lexical: Primary lexical used by this step.
        semantic: Primary semantic used by this step.
        matched_terms: Primary matched terms used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return bool(
        (matched_terms and (lexical >= 0.15 or semantic >= 0.12))
        or lexical >= 0.3
        or semantic >= 0.22
    )


def confidence(lexical: float, semantic: float, hybrid: float, matched_terms: list[str]) -> str:
    """Confidence the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        lexical: Primary lexical used by this step.
        semantic: Primary semantic used by this step.
        hybrid: Primary hybrid used by this step.
        matched_terms: Primary matched terms used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if hybrid >= 0.55 and lexical >= 0.25 and matched_terms:
        return 'high'
    if hybrid >= 0.3 and (matched_terms or semantic >= 0.2):
        return 'medium'
    return 'low'


def rationale(matched_terms: list[str], recency: float, suite_affinity: float, scope_score_value: float) -> str:
    """Rationale the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        matched_terms: Primary matched terms used by this step.
        recency: Primary recency used by this step.
        suite_affinity: Primary suite affinity used by this step.
        scope_score_value: Primary scope score value used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    parts = []
    if matched_terms:
        parts.append(f'matched terms: {", ".join(matched_terms)}')
    if recency >= 0.8:
        parts.append('recently indexed evidence')
    if suite_affinity >= 0.5:
        parts.append('strong suite/path affinity')
    if scope_score_value >= 0.9:
        parts.append('target-repo evidence')
    return '; '.join(parts) or 'weak indirect signal'
