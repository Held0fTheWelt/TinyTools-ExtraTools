"""Context pack summary for fy_platform.ai.semantic_index.

"""
from __future__ import annotations

from fy_platform.ai.schemas.common import RetrievalHit


def pack_confidence(hits: list[RetrievalHit]) -> str:
    """Pack confidence.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        hits: Primary hits used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    # Branch on not hits so pack_confidence only continues along the matching state
    # path.
    if not hits:
        return 'low'
    levels = [hit.confidence for hit in hits[:3]]
    # Branch on levels.count('high') >= 2 so pack_confidence only continues along the
    # matching state path.
    if levels.count('high') >= 2:
        return 'high'
    # Branch on 'medium' in levels or 'high' in levels so pack_confidence only continues
    # along the matching state path.
    if 'medium' in levels or 'high' in levels:
        return 'medium'
    return 'low'


def priorities(query: str, hits: list[RetrievalHit]) -> list[str]:
    """Priorities the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        query: Free-text input that shapes this operation.
        hits: Primary hits used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not hits:
        return [f'Collect more evidence for query "{query}" before acting.']
    result = [f'Start with {hits[0].source_path} because it currently has the strongest combined signal.']
    if len(hits) > 1:
        result.append(f'Compare it with {hits[1].source_path} before deciding on outward action.')
    suites = sorted({hit.suite for hit in hits})
    if len(suites) > 1:
        result.append(f'Use the cross-suite overlap across {", ".join(suites)} to avoid isolated decisions.')
    return result[:4]


def next_steps(hits: list[RetrievalHit], audience: str) -> list[str]:
    """Next steps.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        hits: Primary hits used by this step.
        audience: Free-text input that shapes this operation.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not hits:
        return ['Re-run the relevant suite or index more evidence before building a context pack.']
    steps = [f'Open {hits[0].source_path} first.']
    if audience == 'manager':
        steps.append('Read the plain summary first and only open deep artifacts where the summary is still unclear.')
    elif audience == 'operator':
        steps.append('Check the top evidence and then verify the latest run status before outward application.')
    else:
        steps.append('Use the top two hits to validate the next code or governance action.')
    if any(hit.confidence == 'low' for hit in hits[:2]):
        steps.append('Treat the weaker hits as hints, not proof.')
    return steps[:4]


def pack_uncertainty(hits: list[RetrievalHit]) -> list[str]:
    """Pack uncertainty.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        hits: Primary hits used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not hits:
        return ['no_hits']
    flags: list[str] = []
    if hits[0].confidence == 'low':
        flags.append('top_hit_low_confidence')
    if len(hits) > 1 and abs(hits[0].score_hybrid - hits[1].score_hybrid) < 0.05:
        flags.append('top_hits_close_together')
    if any(not hit.matched_terms for hit in hits[:3]):
        flags.append('weak_term_overlap_present')
    return flags


def summarize_hits(query: str, hits: list[RetrievalHit], *, audience: str = 'developer') -> str:
    """Summarize hits.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        query: Free-text input that shapes this operation.
        hits: Primary hits used by this step.
        audience: Free-text input that shapes this operation.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if not hits:
        return f'No indexed evidence matched query: {query}. The safe next step is to collect more evidence first.'
    top = hits[0]
    suites = sorted({hit.suite for hit in hits})
    if audience == 'manager':
        return f'Found {len(hits)} useful evidence hits for "{query}". The clearest starting point is {top.source_path}. Review that first, then only open more detail where needed.'
    if audience == 'operator':
        return f'Found {len(hits)} evidence hits for "{query}" across suites {suites}. Start with {top.source_path}, then confirm the latest suite run before applying anything outward.'
    return f'Found {len(hits)} indexed evidence hits for query "{query}" across suites {suites}. Strongest source: {top.source_path}. Use the top-ranked items first and treat lower-confidence hits as hints.'
