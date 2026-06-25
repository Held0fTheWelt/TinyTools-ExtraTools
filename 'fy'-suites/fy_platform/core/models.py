"""Suite-neutral shared semantic models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["critical", "high", "medium", "low", "informational"]
Status = Literal["open", "in_progress", "closed", "skipped"]
Mode = Literal["exploratory", "guided", "governed", "strict"]


@dataclass(frozen=True)
class Evidence:
    """Evidence supporting a finding or verification result."""

    kind: str
    source_path: str
    deterministic: bool
    excerpt: str = ""
    content_hash: str = ""


@dataclass(frozen=True)
class Finding:
    """Suite-neutral finding shape."""

    id: str
    suite: str
    category: str
    severity: Severity
    confidence: float
    summary: str
    scope: str
    references: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to a produced artifact."""

    kind: str
    path: str
    format: str
    producer_suite: str
    generated_at: str


@dataclass(frozen=True)
class VerificationResult:
    """Shared verification status shape."""

    status: Status
    checks: list[str]
    failures: list[str]
    evidence_refs: list[str] = field(default_factory=list)


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses into json-serializable structures.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        value: Primary value used by this step.

    Returns:
        Any:
            Value produced by this callable as ``Any``.
    """
    # Branch on hasattr(value, '__dataclass_fields__') so to_jsonable only continues
    # along the matching state path.
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    # Branch on isinstance(value, list) so to_jsonable only continues along the matching
    # state path.
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    # Branch on isinstance(value, dict) so to_jsonable only continues along the matching
    # state path.
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value
