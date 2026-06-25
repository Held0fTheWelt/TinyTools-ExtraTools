"""
Internal JSON-serialisable contract governance model.

Normative vs observed --------------------- ``authority_level``
distinguishes **normative** intent (declared, governed) from
**observed** implementation surfaces. Contractify never promotes
observed behaviour to normative truth automatically; drift findings may
flag misalignment instead.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

AuthorityLevel = Literal["normative", "observed", "verification", "legacy_unverified"]
AnchorKind = Literal[
    "document",
    "machine_schema",
    "workflow_definition",
    "generated_manifest",
    "code_boundary",
    "inventory_hub",
    "unknown",
]
ContractStatus = Literal["active", "deprecated", "archived", "superseded", "experimental", "candidate"]
Layer = Literal[
    "planning",
    "governance",
    "architecture",
    "runtime",
    "api",
    "policy",
    "workflow",
    "implementation",
    "testing",
    "documentation",
    "operations",
    "ui_communication",
    "ai_machine",
]
DriftClass = Literal[
    "anchor_projection",
    "code_documentation",
    "code_test",
    "api_runtime",
    "planning_implementation",
    "duplicate_contract",
    "missing_propagation",
    "retired_surface",
    "conflicting_projections",
    "suite_handoff",
]
DriftSeverity = Literal["critical", "high", "medium", "low", "informational"]
AutomationTier = Literal["auto_high", "curator_review", "candidate_only"]
PrecedenceTier = Literal[
    "runtime_authority",
    "slice_normative",
    "implementation_evidence",
    "verification_evidence",
    "projection_low",
]


def automation_tier(confidence: float) -> AutomationTier:
    """Repository automation policy: avoid false authority on weak
    evidence.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        confidence: Primary confidence used by this step.

    Returns:
        AutomationTier:
            Value produced by this callable as
            ``AutomationTier``.
    """
    # Branch on confidence >= 0.9 so automation_tier only continues along the matching
    # state path.
    if confidence >= 0.9:
        return "auto_high"
    # Branch on confidence >= 0.6 so automation_tier only continues along the matching
    # state path.
    if confidence >= 0.6:
        return "curator_review"
    return "candidate_only"


@dataclass
class RelationEdge:
    """Directed relationship between contracts or between a contract and an
    artifact.
    """

    relation: str
    source_id: str
    target_id: str
    evidence: str
    confidence: float


@dataclass
class ProjectionRecord:
    """Derived view; must reference an anchored contract (may be soft reference
    in prose).
    """

    id: str
    title: str
    path: str
    audience: str
    mode: str
    source_contract_id: str
    anchor_location: str
    authoritative: bool
    confidence: float
    evidence: str
    contract_version_ref: str = ""
    precedence_tier: PrecedenceTier = "projection_low"


@dataclass
class DriftFinding:
    """Evidence-backed drift signal (deterministic or heuristic)."""

    id: str
    drift_class: DriftClass
    summary: str
    evidence_sources: list[str]
    confidence: float
    severity: DriftSeverity
    deterministic: bool
    recommended_follow_up: str
    involved_contract_ids: list[str] = field(default_factory=list)


@dataclass
class ConflictFinding:
    """Material disagreement between sources; human review when ambiguity
    remains.
    """

    id: str
    conflict_type: str
    summary: str
    sources: list[str]
    confidence: float
    requires_human_review: bool
    notes: str = ""
    # Triage metadata (optional; keep JSON stable with explicit defaults).
    classification: str = "other"
    normative_sources: list[str] = field(default_factory=list)
    observed_or_projection_sources: list[str] = field(default_factory=list)
    # Stable kind string for dashboards (defaults to ``conflict_type`` when empty).
    kind: str = ""
    severity: DriftSeverity = "medium"
    normative_candidates: list[str] = field(default_factory=list)
    observed_candidates: list[str] = field(default_factory=list)
    projection_candidates: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Post init.

        Control flow branches on the parsed state rather than relying on
        one linear path.
        """
        if not self.kind:
            self.kind = self.conflict_type


@dataclass
class ContractRecord:
    """Anchored or candidate contract."""

    id: str
    title: str
    summary: str
    contract_type: str
    layer: Layer
    status: ContractStatus
    version: str
    authority_level: AuthorityLevel
    anchor_kind: AnchorKind
    anchor_location: str
    source_of_truth: bool
    derived_from: list[str]
    implemented_by: list[str]
    validated_by: list[str]
    documented_in: list[str]
    projected_as: list[str]
    audiences: list[str]
    modes: list[str]
    scope: str
    owner_or_area: str
    confidence: float
    drift_signals: list[str]
    notes: str
    last_verified: str
    change_risk: str
    tags: list[str]
    discovery_reason: str
    precedence_tier: PrecedenceTier = "slice_normative"


def serialise(obj: Any) -> Any:
    """Convert dataclasses to JSON-friendly structures.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        obj: Primary obj used by this step.

    Returns:
        Any:
            Value produced by this callable as ``Any``.
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {k: serialise(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [serialise(x) for x in obj]
    if isinstance(obj, dict):
        return {k: serialise(v) for k, v in obj.items()}
    return obj
