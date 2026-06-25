"""Readiness and closure schema dataclasses for fy_platform.ai.schemas."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReadinessCase:
    """Structured data container for a readiness-case artifact."""
    readiness_case_id: str
    target_id: str
    target_kind: str
    active_profile: str
    readiness_status: str
    summary: str
    blocker_ids: list[str] = field(default_factory=list)
    obligation_ids: list[str] = field(default_factory=list)
    sufficiency_verdict_id: str = ''
    cannot_honestly_claim_id: str = ''
    residue_ids: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    schema_version: str = 'fy.readiness-case.v1'


@dataclass(frozen=True)
class BlockerGraph:
    """Structured data container for a blocker-graph artifact."""
    blocker_graph_id: str
    target_id: str
    nodes: list[dict[str, object]] = field(default_factory=list)
    edges: list[dict[str, str]] = field(default_factory=list)
    summary: str = ''
    schema_version: str = 'fy.blocker-graph.v1'


@dataclass(frozen=True)
class BlockerPriorityReport:
    """Structured data container for blocker prioritization results."""
    report_id: str
    target_id: str
    blocker_count: int
    priorities: list[dict[str, object]] = field(default_factory=list)
    summary: str = ''
    schema_version: str = 'fy.blocker-priority-report.v1'


@dataclass(frozen=True)
class ObligationMatrix:
    """Structured data container for an obligation matrix."""
    obligation_matrix_id: str
    target_id: str
    rows: list[dict[str, object]] = field(default_factory=list)
    summary: str = ''
    schema_version: str = 'fy.obligation-matrix.v1'


@dataclass(frozen=True)
class SufficiencyVerdict:
    """Structured data container for proof sufficiency judgments."""
    sufficiency_verdict_id: str
    target_id: str
    verdict: str
    reason: str
    supporting_artifact_paths: list[str] = field(default_factory=list)
    schema_version: str = 'fy.sufficiency-verdict.v1'


@dataclass(frozen=True)
class CannotHonestlyClaim:
    """Structured data container for blocked claims."""
    cannot_honestly_claim_id: str
    target_id: str
    blocked_claims: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    schema_version: str = 'fy.cannot-honestly-claim.v1'


@dataclass(frozen=True)
class ClosurePack:
    """Structured data container for closure-pack scaffolds."""
    closure_pack_id: str
    target_id: str
    status: str
    obligation_ids: list[str] = field(default_factory=list)
    residue_ids: list[str] = field(default_factory=list)
    review_required: bool = True
    summary: str = ''
    schema_version: str = 'fy.closure-pack.v1'


@dataclass(frozen=True)
class ResidueLedger:
    """Structured data container for explicit remaining residue."""
    residue_ledger_id: str
    target_id: str
    items: list[dict[str, object]] = field(default_factory=list)
    summary: str = ''
    schema_version: str = 'fy.residue-ledger.v1'


@dataclass(frozen=True)
class ActiveStrategyProfile:
    """Structured data container for the active strategy profile."""
    active_profile: str
    profile_label: str
    default_progression_order: list[str] = field(default_factory=list)
    progression_mode: str = 'progressive'
    allow_profile_switching: bool = True
    menu_enabled: bool = True
    trigger_enabled: bool = True
    command_enabled: bool = True
    markdown_override_allowed: bool = True
    require_review_by_default: bool = True
    auto_apply_level: str = 'none'
    abstain_when_evidence_is_weak: bool = True
    release_honesty_strict: bool = True
    diagnosta_enabled: bool = True
    diagnosta_scope: str = 'claim_and_mvp'
    diagnosta_emit_blocker_graph: bool = True
    diagnosta_emit_cannot_honestly_claim: bool = True
    coda_enabled: bool = True
    coda_scope: str = 'closure_pack_only'
    coda_review_packets_required: bool = True
    coda_require_obligations: bool = True
    coda_require_residue_reporting: bool = True
    emit_profile_to_run_journal: bool = True
    emit_profile_to_observifyfy: bool = True
    emit_profile_to_compare_runs: bool = True
    emit_profile_to_status_pages: bool = True
    compare_profile_effects: str = 'optional'
    allow_candidate_e_features: bool = False
    candidate_e_requires_explicit_opt_in: bool = True
    source_path: str = ''
    schema_version: str = 'fy.active-strategy-profile.v1'
