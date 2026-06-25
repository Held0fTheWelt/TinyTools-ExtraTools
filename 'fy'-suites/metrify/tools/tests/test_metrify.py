"""Tests for metrify.

"""
from __future__ import annotations

import json
from pathlib import Path

from metrify.tools.ledger import append_event, compute_cost
from metrify.tools.models import UsageEvent
from metrify.tools.reporting import build_summary


def test_compute_cost_uses_catalog() -> None:
    """Verify that compute cost uses catalog works as expected.
    """
    cost = compute_cost('gpt-5.4', 'standard', 1_000_000, 0, 1_000_000)
    assert cost == 17.5


def test_summary_rollups(tmp_path: Path) -> None:
    """Verify that summary rollups works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    ledger = tmp_path / 'ledger.jsonl'
    append_event(ledger, UsageEvent(timestamp_utc='2026-04-18T00:00:00+00:00', suite='contractify', run_id='r1', model='gpt-5.4-mini', input_tokens=1000, output_tokens=500, cost_usd=0.003))
    append_event(ledger, UsageEvent(timestamp_utc='2026-04-18T01:00:00+00:00', suite='documentify', run_id='r2', model='gpt-5.4', input_tokens=2000, output_tokens=800, cost_usd=0.02, technique_tags=['rag']))
    summary = build_summary(ledger)
    assert summary['event_count'] == 2
    assert summary['run_count'] == 2
    assert summary['total_cost_usd'] == 0.023
    assert summary['top_models'][0]['key'] == 'gpt-5.4'
