"""Execution plan for fy_platform.runtime.

"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LaneStep:
    """Coordinate lane step behavior.
    """
    lane_name: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    """Coordinate execution plan behavior.
    """
    public_command: str
    mode_name: str
    lens: str
    steps: list[LaneStep]
    provider_allowed: bool
    deterministic_first: bool = True
    review_required: bool = False
