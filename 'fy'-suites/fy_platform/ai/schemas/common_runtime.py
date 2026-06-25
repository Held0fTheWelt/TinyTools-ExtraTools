"""Common runtime for fy_platform.ai.schemas.

"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepositorySnapshot:
    """Coordinate repository snapshot behavior.
    """
    snapshot_id: str
    repo_root: str
    fingerprint: str
    created_at: str
    source_ref: str = ''
    branch_ref: str = ''
    commit_ref: str = ''
    scan_scope: str = 'full'


@dataclass(frozen=True)
class RepoAsset:
    """Coordinate repo asset behavior.
    """
    asset_id: str
    snapshot_id: str
    path: str
    kind: str
    language: str
    role: str
    ownership_zone: str
    content_hash: str
    is_generated: bool = False
    suite_origin: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructureFinding:
    """Coordinate structure finding behavior.
    """
    finding_id: str
    finding_kind: str
    severity: str
    confidence: str
    summary: str
    asset_ids: list[str] = field(default_factory=list)
    related_ids: list[str] = field(default_factory=list)
    recommended_action: str = ''


@dataclass(frozen=True)
class DecisionRecord:
    """Structured data container for decision record.
    """
    decision_id: str
    decision_kind: str
    lane: str
    reason: str
    confidence: str
    recommended_action: str
    uncertainty_flags: list[str] = field(default_factory=list)
    source_evidence_ids: list[str] = field(default_factory=list)
    created_at: str = ''


@dataclass(frozen=True)
class ReviewTask:
    """Coordinate review task behavior.
    """
    review_task_id: str
    subject_kind: str
    subject_id: str
    reason: str
    priority: str
    requested_by_lane: str
    blocking: bool = False
    status: str = 'open'
    assignee: str = ''


@dataclass(frozen=True)
class LaneExecutionRecord:
    """Structured data container for lane execution record.
    """
    lane_execution_id: str
    run_id: str
    public_command: str
    mode_name: str
    lane_name: str
    status: str
    detail: dict[str, Any] = field(default_factory=dict)
    output_refs: list[str] = field(default_factory=list)
    started_at: str = ''
    ended_at: str | None = None


@dataclass(frozen=True)
class ProviderCallRecord:
    """Structured data container for provider call record.
    """
    provider_call_id: str
    run_id: str
    lane_execution_id: str
    task_type: str
    provider: str
    model: str
    budget_class: str
    prompt_hash: str
    context_hash: str
    cache_key: str
    cache_hit: bool
    guard_allowed: bool
    allow_reason: str
    deny_reason: str
    expected_utility: float
    result_status: str
    created_at: str


@dataclass(frozen=True)
class SurfaceAlias:
    """Coordinate surface alias behavior.
    """
    alias_id: str
    legacy_surface: str
    current_surface: str
    status: str
    sunset_phase: str
