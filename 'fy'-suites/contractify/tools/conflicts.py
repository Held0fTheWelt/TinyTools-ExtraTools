"""
Conflict detection — deterministic anchors first, then bounded
heuristics.

Every ``ConflictFinding`` records ``classification`` for backlog triage.
Human review is required when ``requires_human_review`` is true unless
confidence is explicitly high for a mechanical clash (duplicate
normative table targets).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote

from fy_platform.core.manifest import load_manifest, suite_config
from contractify.tools.adr_governance import discover_adr_governance, iter_adr_markdown_paths
from contractify.tools.discovery import NORMATIVE_INDEX, OPENAPI_DEFAULT, POSTMAN_MANIFEST
from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord
from contractify.tools.runtime_mvp_spine import build_runtime_mvp_spine
from contractify.tools.versioning import adr_declared_status, openapi_sha256_prefix

# Markdown table / inline link targets from normative index (same cell patterns as human editors use).
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

# ADR vocabulary buckets (bounded overlap heuristic — not semantic contradiction proof).
_ADR_OVERLAP_TERMS = (
    ("scene identity", ("scene identity", "scene_id", "scene-id")),
    ("session surface", ("session surface", "session_surface", "session")),
    ("runtime authority", ("runtime authority", "runtime_authority", "authority")),
)

_GOVERNED_RUNTIME_SPINE_OVERLAPS: dict[str, set[str]] = {
    "session surface": {
        "adr-0001-runtime-authority-in-world-engine.md",
        "adr-0002-backend-session-surface-quarantine.md",
    },
    "runtime authority": {
        "adr-0001-runtime-authority-in-world-engine.md",
        "adr-0002-backend-session-surface-quarantine.md",
    },
}


def _openapi_default(repo: Path) -> str:
    """Openapi default.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    # Read and normalize the input data before _openapi_default branches on or
    # transforms it further.
    manifest, _warnings = load_manifest(repo)
    cfg = suite_config(manifest, "contractify")
    rel = str(cfg.get("openapi", "")).strip() if cfg else ""
    return rel or OPENAPI_DEFAULT


def _norm_index_link(repo: Path, index_dir: Path, raw_target: str) -> str:
    """Resolve link target relative to the normative index directory;
    return repo-posix path.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        index_dir: Root directory used to resolve repository-local
            paths.
        raw_target: Primary raw target used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    t = unquote(raw_target.strip().split("#", 1)[0].strip())
    if not t or t.startswith(("http://", "https://", "mailto:")):
        return ""
    resolved = (index_dir / t).resolve()
    try:
        return resolved.relative_to(repo.resolve()).as_posix()
    except ValueError:
        return ""




def _governed_runtime_spine_overlap(bucket: str, hits: list[str]) -> bool:
    """Governed runtime spine overlap.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        bucket: Primary bucket used by this step.
        hits: Primary hits used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    governed = _GOVERNED_RUNTIME_SPINE_OVERLAPS.get(bucket)
    if not governed:
        return False
    return set(hits).issubset(governed)

def detect_duplicate_normative_index_targets(repo: Path) -> list[ConflictFinding]:
    """Two or more index rows link to the same resolved path — anchor
    ambiguity (deterministic).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    repo = repo.resolve()
    p = repo / NORMATIVE_INDEX
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    index_dir = p.parent
    counts: dict[str, list[str]] = {}
    for _label, target in _MD_LINK.findall(text):
        norm = _norm_index_link(repo, index_dir, target)
        if not norm:
            continue
        counts.setdefault(norm, []).append(target.strip())

    out: list[ConflictFinding] = []
    for norm, raw_list in counts.items():
        if len(raw_list) < 2:
            continue
        out.append(
            ConflictFinding(
                id=f"CNF-NORM-DUP-{hashlib.sha256(norm.encode()).hexdigest()[:10]}",
                conflict_type="duplicate_normative_navigation_target",
                summary=f"Normative index lists the same resolved target more than once: {norm}",
                sources=[NORMATIVE_INDEX, norm],
                confidence=0.95,
                requires_human_review=False,
                notes="Mechanical duplicate-link detection in the index markdown.",
                classification="normative_anchor_ambiguity",
                normative_sources=[NORMATIVE_INDEX],
                observed_or_projection_sources=[],
                kind="conflicting_candidate_anchors",
                severity="high",
                normative_candidates=[NORMATIVE_INDEX, norm],
            )
        )
    return out


def detect_adr_vocabulary_overlap(repo: Path) -> list[ConflictFinding]:
    """Multiple ADRs hit the same bounded vocabulary bucket (heuristic
    overlap).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[ConflictFinding] = []
    for bucket, keywords in _ADR_OVERLAP_TERMS:
        hits: list[str] = []
        for adr in iter_adr_markdown_paths(repo):
            text = adr.read_text(encoding="utf-8", errors="replace").lower()
            if any(k.lower() in text for k in keywords):
                hits.append(adr.name)
        if len(hits) >= 2:
            if _governed_runtime_spine_overlap(bucket, hits):
                continue
            out.append(
                ConflictFinding(
                    id=f"CNF-ADR-VOC-{hashlib.sha256(bucket.encode()).hexdigest()[:8]}",
                    conflict_type="adr_vocabulary_overlap",
                    summary=f"Multiple ADRs reference the same governance vocabulary bucket “{bucket}”; "
                    "check supersession and single-current-truth narrative.",
                    sources=hits,
                    confidence=0.55,
                    requires_human_review=True,
                    notes="Keyword bucket overlap only — not proof of logical contradiction.",
                    classification="normative_vocabulary_overlap",
                    normative_sources=hits,
                    observed_or_projection_sources=[],
                    kind="conflicting_normative_claims",
                    severity="medium",
                    normative_candidates=hits,
                )
            )
    return out


def detect_projection_fingerprint_mismatch(
    repo: Path,
    projections: list[ProjectionRecord],
) -> list[ConflictFinding]:
    """Projection ``contract_version_ref`` is a 16-hex OpenAPI prefix that
    disagrees with disk (deterministic).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        projections: Primary projections used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    repo = repo.resolve()
    openapi_default = _openapi_default(repo)
    openapi = repo / openapi_default
    if not openapi.is_file():
        return []
    full_sha = hashlib.sha256(openapi.read_bytes()).hexdigest()
    prefix = openapi_sha256_prefix(full_sha)
    out: list[ConflictFinding] = []
    for pr in projections:
        ref = (pr.contract_version_ref or "").strip().lower()
        if len(ref) != 16 or any(c not in "0123456789abcdef" for c in ref):
            continue
        if ref == prefix:
            continue
        out.append(
            ConflictFinding(
                id=f"CNF-PRJ-SHA-{hashlib.sha256(pr.path.encode()).hexdigest()[:10]}",
                conflict_type="projection_openapi_fingerprint_mismatch",
                summary=f"Projection {pr.path} declares openapi fingerprint prefix {ref!r} but "
                f"current OpenAPI SHA256 prefix is {prefix!r}.",
                sources=[pr.path, openapi_default, POSTMAN_MANIFEST],
                confidence=1.0,
                requires_human_review=False,
                notes="Treat as stale projection or wrong manifest until regenerated.",
                classification="projection_anchor_mismatch",
                normative_sources=[openapi_default],
                observed_or_projection_sources=[pr.path],
                kind="stale_projection_vs_openapi_anchor",
                severity="high",
                normative_candidates=[openapi_default],
                projection_candidates=[pr.path],
            )
        )
    return out


def detect_deprecated_adr_without_supersession_link(repo: Path) -> list[ConflictFinding]:
    """Explicit ``Status: Deprecated`` / ``Superseded`` without
    supersession navigation (bounded header scan).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[ConflictFinding] = []
    linkish = re.compile(r"supersed|superseded\s+by|replaced\s+by", re.IGNORECASE)
    bad_status = re.compile(r"(?im)^\s*\*{0,2}status\*{0,2}\s*:\s*(deprecated|superseded)\b")
    for adr in iter_adr_markdown_paths(repo):
        head = adr.read_text(encoding="utf-8", errors="replace")[:6000]
        if not bad_status.search(head):
            continue
        if linkish.search(head):
            continue
        rel = adr.relative_to(repo).as_posix()
        out.append(
            ConflictFinding(
                id=f"CNF-ADR-LIFE-{adr.stem[:20]}",
                conflict_type="lifecycle_supersession_gap",
                summary=f"ADR {rel} declares deprecated/superseded status in the header but no explicit supersession "
                "navigation pattern — add a link to the replacement anchor.",
                sources=[rel],
                confidence=0.62,
                requires_human_review=True,
                notes="Header-only scan for Status + supersession cues.",
                classification="supersession_gap",
                normative_sources=[rel],
                observed_or_projection_sources=[],
                kind="lifecycle_version_or_supersession_conflict",
                severity="medium",
                normative_candidates=[rel],
            )
        )
    return out


_ACTIVE_BINDING_ROW = re.compile(r"\b(active|binding)\b", re.IGNORECASE)


def detect_active_index_row_links_retired_adr(repo: Path) -> list[ConflictFinding]:
    """Index markdown row reads Active/Binding but links to an ADR whose
    declared status is retired.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    repo = repo.resolve()
    p = repo / NORMATIVE_INDEX
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8", errors="replace")
    index_dir = p.parent
    adr_paths = {adr.relative_to(repo).as_posix() for adr in iter_adr_markdown_paths(repo)}
    out: list[ConflictFinding] = []
    for line in text.splitlines():
        if "|" not in line or not _ACTIVE_BINDING_ROW.search(line):
            continue
        for _label, target in _MD_LINK.findall(line):
            norm = _norm_index_link(repo, index_dir, target)
            if not norm or norm not in adr_paths:
                continue
            adr_path = repo / norm.replace("\\", "/")
            if not adr_path.is_file():
                continue
            head = adr_path.read_text(encoding="utf-8", errors="replace")[:8000]
            st = adr_declared_status(head)
            if st not in ("superseded", "deprecated"):
                continue
            rel = adr_path.relative_to(repo).as_posix()
            out.append(
                ConflictFinding(
                    id=f"CNF-IDX-RET-{hashlib.sha256(line.encode()).hexdigest()[:10]}",
                    conflict_type="lifecycle_index_row_vs_retired_adr",
                    summary=f"Normative index row suggests current/binding navigation but links to retired ADR {rel} "
                    f"(declared status line resolves to {st}).",
                    sources=[NORMATIVE_INDEX, rel, line.strip()[:240]],
                    confidence=0.88,
                    requires_human_review=True,
                    notes="Table-row heuristic — legitimate history rows should use Retired/History labelling instead of Active/Binding.",
                    classification="superseded_still_referenced_as_current",
                    normative_sources=[NORMATIVE_INDEX, rel],
                    observed_or_projection_sources=[],
                    kind="superseded_contract_still_active_navigation",
                    severity="high",
                    normative_candidates=[NORMATIVE_INDEX, rel],
                )
            )
    return out


def detect_projection_pins_retired_source_contract(
    projections: list[ProjectionRecord],
    contract_status_by_id: dict[str, str],
) -> list[ConflictFinding]:
    """Projection declares a ``source_contract_id`` whose discovered
    lifecycle is retired (bounded inventory check).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        projections: Primary projections used by this step.
        contract_status_by_id: Identifier used to select an existing run
            or record.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not contract_status_by_id:
        return []
    out: list[ConflictFinding] = []
    for pr in projections:
        sid = (pr.source_contract_id or "").strip()
        if not sid:
            continue
        st = contract_status_by_id.get(sid)
        if st not in ("superseded", "deprecated"):
            continue
        out.append(
            ConflictFinding(
                id=f"CNF-PRJ-RET-{hashlib.sha256((pr.id + sid).encode()).hexdigest()[:10]}",
                conflict_type="projection_pins_retired_contract",
                summary=f"Projection {pr.path} pins source_contract_id={sid!r} but that contract's lifecycle is {st!r} "
                "— verify whether the projection should migrate to the successor anchor.",
                sources=[pr.path, sid],
                confidence=0.85,
                requires_human_review=True,
                notes="History/museum projections may be intentional; this is a visibility signal, not auto-fail.",
                classification="lifecycle_projection_vs_retired_anchor",
                normative_sources=[sid],
                observed_or_projection_sources=[pr.path],
                kind="stale_projection_vs_lifecycle_anchor",
                severity="high",
                normative_candidates=[sid],
                projection_candidates=[pr.path],
            )
        )
    return out


def detect_projection_orphan_source_contract(
    projections: list[ProjectionRecord],
    contract_ids: frozenset[str],
) -> list[ConflictFinding]:
    """Projection references a ``source_contract_id`` that is not in the
    discovered contract inventory.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        projections: Primary projections used by this step.
        contract_ids: Primary contract ids used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not contract_ids:
        return []
    out: list[ConflictFinding] = []
    for pr in projections:
        sid = (pr.source_contract_id or "").strip()
        if not sid or sid in contract_ids:
            continue
        out.append(
            ConflictFinding(
                id=f"CNF-PRJ-ORPH-{hashlib.sha256(pr.id.encode()).hexdigest()[:10]}",
                conflict_type="projection_orphan_source_contract",
                summary=f"Projection {pr.path} references source_contract_id={sid!r} but that id was not discovered "
                "in this pass (missing anchor, typo, or discovery ceiling).",
                sources=[pr.path, sid],
                confidence=0.92,
                requires_human_review=True,
                notes="Non-resolution: widen discovery, fix manifest metadata, or correct the projection block.",
                classification="projection_anchor_mismatch",
                normative_sources=[],
                observed_or_projection_sources=[pr.path],
                kind="projection_to_anchor_mismatch",
                severity="high",
                projection_candidates=[pr.path],
                normative_candidates=[sid],
            )
        )
    return out


def detect_all_conflicts(
    repo: Path,
    projections: list[ProjectionRecord],
    *,
    contract_ids: frozenset[str] | None = None,
    contracts: list[ContractRecord] | None = None,
) -> list[ConflictFinding]:
    """Run all conflict passes; de-duplicate by ``id``.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        projections: Primary projections used by this step.
        contract_ids: Primary contract ids used by this step.
        contracts: Primary contracts used by this step.

    Returns:
        list[ConflictFinding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    all_c: list[ConflictFinding] = []
    all_c.extend(detect_duplicate_normative_index_targets(repo))
    all_c.extend(detect_adr_vocabulary_overlap(repo))
    all_c.extend(detect_projection_fingerprint_mismatch(repo, projections))
    all_c.extend(detect_deprecated_adr_without_supersession_link(repo))
    all_c.extend(detect_active_index_row_links_retired_adr(repo))
    if contracts is not None:
        all_c.extend(
            detect_projection_pins_retired_source_contract(
                projections,
                {c.id: c.status for c in contracts},
            )
        )
    if contract_ids:
        all_c.extend(detect_projection_orphan_source_contract(projections, contract_ids))
    _curated_contracts, _curated_projections, _curated_relations, curated_conflicts, _curated_families = build_runtime_mvp_spine(repo)
    all_c.extend(curated_conflicts)
    seen: set[str] = set()
    uniq: list[ConflictFinding] = []
    for c in all_c:
        if c.id in seen:
            continue
        seen.add(c.id)
        uniq.append(c)
    return uniq
