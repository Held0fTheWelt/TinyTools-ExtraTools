"""
Add bounded, high-signal relation edges beyond discovery’s core Postman
/ audience edges.
"""
from __future__ import annotations

import re
from pathlib import Path

from contractify.tools.adr_governance import iter_adr_markdown_paths
from contractify.tools.discovery import NORMATIVE_INDEX, OPENAPI_DEFAULT
from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord, RelationEdge
from contractify.tools.versioning import adr_supersedes_line, resolve_supersedes_markdown_target

# Cap index-derived edges to avoid graph explosion (anti-bureaucracy).
_MAX_INDEX_REFERENCE_EDGES = 14


def _adr_contract_id(stem: str) -> str:
    """Adr contract id.

    Args:
        stem: Primary stem used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    slug = stem.upper().replace("-", "_")
    return f"CTR-ADR-{slug[:24]}"


def extend_relations(
    repo: Path,
    contracts: list[ContractRecord],
    projections: list[ProjectionRecord],
    base: list[RelationEdge],
    *,
    conflicts: list[ConflictFinding] | None = None,
) -> list[RelationEdge]:
    """Return ``base`` plus a small set of deterministic cross-links.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo: Primary repo used by this step.
        contracts: Primary contracts used by this step.
        projections: Primary projections used by this step.
        base: Primary base used by this step.
        conflicts: Primary conflicts used by this step.

    Returns:
        list[RelationEdge]:
            Collection produced from the parsed or
            accumulated input data.
    """
    repo = repo.resolve()
    out: list[RelationEdge] = list(base)
    ids = {c.id for c in contracts}

    idx_path = repo / NORMATIVE_INDEX
    if idx_path.is_file() and "CTR-NORM-INDEX-001" in ids:
        text = idx_path.read_text(encoding="utf-8", errors="replace")
        if "openapi" in text.lower() and "CTR-API-OPENAPI-001" in ids:
            out.append(
                RelationEdge(
                    relation="references",
                    source_id="CTR-NORM-INDEX-001",
                    target_id="CTR-API-OPENAPI-001",
                    evidence="Normative index prose references the HTTP/OpenAPI contract surface.",
                    confidence=0.82,
                )
            )
        # Table targets that look like slice / runtime docs (bounded).
        seen_idx: set[str] = set()
        for m in re.finditer(r"\]\((\.\./[^)]+?\.md)\)", text):
            if len(out) >= len(base) + _MAX_INDEX_REFERENCE_EDGES:
                break
            raw = m.group(1).strip()
            resolved = (idx_path.parent / raw).resolve()
            try:
                rel = resolved.relative_to(repo).as_posix()
            except ValueError:
                continue
            if not resolved.is_file():
                continue
            tid = f"DOC:{rel}"
            if tid in seen_idx:
                continue
            seen_idx.add(tid)
            out.append(
                RelationEdge(
                    relation="indexes",
                    source_id="CTR-NORM-INDEX-001",
                    target_id=tid,
                    evidence=f"Normative index table links to {rel}",
                    confidence=0.88,
                )
            )

    if "CTR-API-OPENAPI-001" in ids and (repo / "backend").is_dir():
        out.append(
            RelationEdge(
                relation="implements",
                source_id="CTR-API-OPENAPI-001",
                target_id="OBS:backend/",
                evidence="OpenAPI describes Flask `/api/v1` routes implemented under backend/.",
                confidence=0.72,
            )
        )

    if "CTR-OPS-RUNTIME-001" in ids and "CTR-NORM-INDEX-001" in ids:
        out.append(
            RelationEdge(
                relation="operationalizes",
                source_id="CTR-OPS-RUNTIME-001",
                target_id="CTR-NORM-INDEX-001",
                evidence="Operational runbook translates normative governance into operator-facing procedures.",
                confidence=0.68,
            )
        )

    if "CTR-POSTMANIFY-TASK-001" in ids and "CTR-API-OPENAPI-001" in ids:
        out.append(
            RelationEdge(
                relation="references",
                source_id="CTR-POSTMANIFY-TASK-001",
                target_id="CTR-API-OPENAPI-001",
                evidence="Postmanify procedure consumes the canonical OpenAPI anchor for collection generation.",
                confidence=0.9,
            )
        )

    if "CTR-DOCIFY-TASK-001" in ids and "CTR-CONTRACTIFY-SELF-001" in ids:
        out.append(
            RelationEdge(
                relation="documents",
                source_id="CTR-DOCIFY-TASK-001",
                target_id="CTR-CONTRACTIFY-SELF-001",
                evidence="Docify default roots include contractify; check task documents cross-suite audit obligations.",
                confidence=0.62,
            )
        )

    for adr in iter_adr_markdown_paths(repo):
        head = adr.read_text(encoding="utf-8", errors="replace")[:12_000]
        body = adr_supersedes_line(head)
        if not body:
            continue
        sup = resolve_supersedes_markdown_target(body, adr_file=adr, repo=repo)
        if not sup:
            continue
        tgt_path = repo / sup
        if not tgt_path.is_file():
            continue
        src_id = _adr_contract_id(adr.stem)
        tgt_id = _adr_contract_id(tgt_path.stem)
        if src_id in ids and tgt_id in ids:
            out.append(
                RelationEdge(
                    relation="supersedes",
                    source_id=src_id,
                    target_id=tgt_id,
                    evidence=f"{adr.name} declares explicit Supersedes navigation to {sup}",
                    confidence=0.9,
                )
            )

    wf_dir = repo / ".github" / "workflows"
    if "CTR-API-OPENAPI-001" in ids and wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.yml"))[:6]:
            txt = wf.read_text(encoding="utf-8", errors="replace")[:20_000]
            low = txt.lower()
            if "openapi" not in low and "postman" not in low:
                continue
            rel = wf.relative_to(repo).as_posix()
            out.append(
                RelationEdge(
                    relation="validates",
                    source_id=f"OBS:{rel}",
                    target_id="CTR-API-OPENAPI-001",
                    evidence=f"Workflow {rel} references OpenAPI/Postman artefacts (regeneration or contract checks).",
                    confidence=0.66,
                )
            )
            break

    if conflicts:
        for c in conflicts:
            if c.classification != "normative_anchor_ambiguity":
                continue
            dup = next((x for x in c.normative_candidates if x != NORMATIVE_INDEX), None)
            if not dup:
                continue
            if "CTR-NORM-INDEX-001" not in ids:
                continue
            tid = f"DOC:{dup}"
            out.append(
                RelationEdge(
                    relation="conflicts_with",
                    source_id="CTR-NORM-INDEX-001",
                    target_id=tid,
                    evidence="Normative index lists the same resolved markdown target more than once (navigation ambiguity).",
                    confidence=0.88,
                )
            )

    return out
