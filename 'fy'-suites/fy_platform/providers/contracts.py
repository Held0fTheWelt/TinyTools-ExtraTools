"""Contracts for fy_platform.providers.

"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderCallRequest:
    """Coordinate provider call request behavior.
    """
    task_type: str
    suite_or_mode: str
    run_id: str
    lane_execution_id: str
    provider: str
    model: str
    prompt_hash: str
    context_hash: str
    estimated_tokens: int
    expected_utility: float
    budget_class: str
    allow_provider: bool
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernorDecision:
    """Coordinate governor decision behavior.
    """
    allowed: bool
    reason: str
    policy_lane: str
    cache_key: str
    cache_hit: bool = False
    budget_state: str = 'ok'
