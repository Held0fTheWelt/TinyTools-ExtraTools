"""Compare runs for fy_platform.ai.evidence_registry.

"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.schemas.common import CompareRunsDelta


def build_compare_runs_delta(registry, left_run_id: str, right_run_id: str) -> CompareRunsDelta | None:
    """Build compare runs delta.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        registry: Primary registry used by this step.
        left_run_id: Identifier used to select an existing run or
            record.
        right_run_id: Identifier used to select an existing run or
            record.

    Returns:
        CompareRunsDelta | None:
            Value produced by this callable as
            ``CompareRunsDelta | None``.
    """
    left = registry.get_run(left_run_id)
    right = registry.get_run(right_run_id)
    # Branch on not left or not right so build_compare_runs_delta only continues along
    # the matching state path.
    if not left or not right:
        return None
    # Assemble the structured result data before later steps enrich or return it from
    # build_compare_runs_delta.
    left_art = registry.artifacts_for_run(left_run_id)
    right_art = registry.artifacts_for_run(right_run_id)
    left_ev = registry.evidence_for_run(left_run_id)
    right_ev = registry.evidence_for_run(right_run_id)
    left_roles = {item['role'] for item in left_art}
    right_roles = {item['role'] for item in right_art}
    left_formats = {item['format'] for item in left_art}
    right_formats = {item['format'] for item in right_art}
    left_review_counts = dict(sorted(Counter(item['review_state'] for item in left_ev).items()))
    right_review_counts = dict(sorted(Counter(item['review_state'] for item in right_ev).items()))
    journal = RunJournal(registry.root)
    left_summary = journal.summarize(left['suite'], left_run_id)
    right_summary = journal.summarize(right['suite'], right_run_id)
    return CompareRunsDelta(
        left_run_id=left_run_id,
        right_run_id=right_run_id,
        left_status=left['status'],
        right_status=right['status'],
        artifact_delta=len(right_art) - len(left_art),
        added_roles=sorted(right_roles - left_roles),
        removed_roles=sorted(left_roles - right_roles),
        left_artifact_count=len(left_art),
        right_artifact_count=len(right_art),
        left_evidence_count=len(left_ev),
        right_evidence_count=len(right_ev),
        left_review_state_counts=left_review_counts,
        right_review_state_counts=right_review_counts,
        left_journal_event_count=left_summary['event_count'],
        right_journal_event_count=right_summary['event_count'],
        left_duration_seconds=duration_seconds(left['started_at'], left['ended_at']),
        right_duration_seconds=duration_seconds(right['started_at'], right['ended_at']),
        mode_changed=left['mode'] != right['mode'],
        target_repo_changed=left['target_repo_root'] != right['target_repo_root'],
        target_repo_id_changed=left['target_repo_id'] != right['target_repo_id'],
        left_strategy_profile=left.get('strategy_profile', ''),
        right_strategy_profile=right.get('strategy_profile', ''),
        strategy_profile_changed=left.get('strategy_profile', '') != right.get('strategy_profile', ''),
        added_formats=sorted(right_formats - left_formats),
        removed_formats=sorted(left_formats - right_formats),
    )


def duration_seconds(started_at: str | None, ended_at: str | None) -> float | None:
    """Duration seconds.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        started_at: Primary started at used by this step.
        ended_at: Primary ended at used by this step.

    Returns:
        float | None:
            Value produced by this callable as ``float |
            None``.
    """
    if not started_at or not ended_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
    except ValueError:
        return None
    return round((end - start).total_seconds(), 6)
