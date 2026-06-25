"""
Contract discovery using explicit heuristics (A–E tiers).

A — Explicit contract candidates (high confidence when markers or known
hub paths match). B — Structural boundary candidates (medium):
workflows, public integration surfaces. C — Referencing / audience
artifacts (usually projections, not anchors). D — Out of scope by
default (not scanned here). E — Confidence recorded per row;
``discovery_reason`` explains classification.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from fy_platform.core.manifest import load_manifest, suite_config
from contractify.tools.adr_governance import iter_adr_markdown_paths
from contractify.tools.models import (
    AnchorKind,
    AuthorityLevel,
    ContractRecord,
    ContractStatus,
    Layer,
    ProjectionRecord,
    RelationEdge,
)
from contractify.tools.runtime_mvp_spine import build_runtime_mvp_spine
from contractify.tools.versioning import adr_declared_status, read_openapi_version_from_file

EXPLICIT_MARKER_PATTERNS = (
    re.compile(r"\bnormative\b", re.IGNORECASE),
    re.compile(r"\bcanonical contract\b", re.IGNORECASE),
    re.compile(r"source of truth", re.IGNORECASE),
    re.compile(r"\bbinding scope\b", re.IGNORECASE),
    re.compile(r"\bADR-\d+", re.IGNORECASE),
    re.compile(r"##\s+Normative specification", re.IGNORECASE),
)

NORMATIVE_INDEX = "docs/dev/contracts/normative-contracts-index.md"
OPENAPI_DEFAULT = "docs/api/openapi.yaml"
POSTMAN_MANIFEST = "postman/postmanify-manifest.json"
DESPAG_SETUP = "'fy'-suites/despaghettify/spaghetti-setup.md"
DOCIFY_README = "'fy'-suites/docify/README.md"
POSTMANIFY_SYNC_TASK = "'fy'-suites/postmanify/postmanify-sync-task.md"
DOCIFY_DOCUMENTATION_CHECK_TASK = "'fy'-suites/docify/documentation-check-task.md"

EASY_DOC_GLOB = "docs/easy"
START_HERE_GLOB = "docs/start-here"


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


def _read_head(path: Path, *, max_bytes: int = 48_000) -> str:
    """Read head.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.
        max_bytes: Primary max bytes used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    try:
        raw = path.read_bytes()[:max_bytes]
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _adr_contract_status(raw: str) -> ContractStatus:
    """Map explicit ADR ``Status:`` text to lifecycle enum (conservative
    default: active).

    Args:
        raw: Primary raw used by this step.

    Returns:
        ContractStatus:
            Value produced by this callable as
            ``ContractStatus``.
    """
    m: dict[str, ContractStatus] = {
        "accepted": "active",
        "active": "active",
        "adopted": "active",
        "proposed": "experimental",
        "draft": "experimental",
        "deprecated": "deprecated",
        "superseded": "superseded",
        "archived": "archived",
    }
    return m.get(raw, "active")


def _marker_boost(text: str) -> float:
    """Marker boost.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    hits = sum(1 for p in EXPLICIT_MARKER_PATTERNS if p.search(text))
    return min(0.12, 0.03 * hits)


def _safe_rel(path: Path, repo: Path) -> str:
    """Safe rel.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def _contract(
    *,
    cid: str,
    title: str,
    summary: str,
    contract_type: str,
    layer: Layer,
    status: ContractStatus,
    version: str,
    authority_level: AuthorityLevel,
    anchor_kind: AnchorKind,
    anchor_location: str,
    source_of_truth: bool,
    confidence: float,
    discovery_reason: str,
    tags: list[str],
    owner_or_area: str = "engineering",
    implemented_by: list[str] | None = None,
    validated_by: list[str] | None = None,
    documented_in: list[str] | None = None,
    projected_as: list[str] | None = None,
    derived_from: list[str] | None = None,
    audiences: list[str] | None = None,
    modes: list[str] | None = None,
    notes: str = "",
) -> ContractRecord:
    """Contract the requested operation.

    Args:
        cid: Primary cid used by this step.
        title: Primary title used by this step.
        summary: Structured data carried through this workflow.
        contract_type: Primary contract type used by this step.
        layer: Primary layer used by this step.
        status: Named status for this operation.
        version: Primary version used by this step.
        authority_level: Primary authority level used by this step.
        anchor_kind: Primary anchor kind used by this step.
        anchor_location: Primary anchor location used by this step.
        source_of_truth: Whether to enable this optional behavior.
        confidence: Primary confidence used by this step.
        discovery_reason: Primary discovery reason used by this step.
        tags: Primary tags used by this step.
        owner_or_area: Primary owner or area used by this step.
        implemented_by: Primary implemented by used by this step.
        validated_by: Primary validated by used by this step.
        documented_in: Primary documented in used by this step.
        projected_as: Primary projected as used by this step.
        derived_from: Primary derived from used by this step.
        audiences: Primary audiences used by this step.
        modes: Primary modes used by this step.
        notes: Primary notes used by this step.

    Returns:
        ContractRecord:
            Value produced by this callable as
            ``ContractRecord``.
    """
    return ContractRecord(
        id=cid,
        title=title,
        summary=summary,
        contract_type=contract_type,
        layer=layer,
        status=status,
        version=version,
        authority_level=authority_level,
        anchor_kind=anchor_kind,
        anchor_location=anchor_location,
        source_of_truth=source_of_truth,
        derived_from=derived_from or [],
        implemented_by=implemented_by or [],
        validated_by=validated_by or [],
        documented_in=documented_in or [],
        projected_as=projected_as or [],
        audiences=audiences or ["developer", "architect"],
        modes=modes or ["specialist"],
        scope="repository",
        owner_or_area=owner_or_area,
        confidence=min(0.99, max(0.0, confidence)),
        drift_signals=[],
        notes=notes,
        last_verified="",
        change_risk="unknown",
        tags=tags,
        discovery_reason=discovery_reason,
    )


def discover_contracts_and_projections(
    repo: Path,
    *,
    max_contracts: int = 30,
) -> tuple[list[ContractRecord], list[ProjectionRecord], list[RelationEdge]]:
    """Return contracts, projections, and high-confidence relation edges
    (phase-1 ceiling).

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo: Primary repo used by this step.
        max_contracts: Primary max contracts used by this step.

    Returns:
        tuple[list[ContractRecord], list[ProjectionRecord], list[Re...:
            Collection produced from the parsed or
            accumulated input data.
    """
    repo = repo.resolve()
    openapi_default = _openapi_default(repo)
    p_openapi = repo / openapi_default
    contracts: list[ContractRecord] = []
    projections: list[ProjectionRecord] = []
    relations: list[RelationEdge] = []

    def add(c: ContractRecord) -> None:
        """Add the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            c: Primary c used by this step.
        """
        if len(contracts) >= max_contracts:
            return
        contracts.append(c)

    # A1 — Normative contracts index (hub for many slice contracts)
    p_index = repo / NORMATIVE_INDEX
    has_normative_index = p_index.is_file()
    if has_normative_index:
        head = _read_head(p_index)
        conf = 0.92 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-NORM-INDEX-001",
                title="Normative contracts index",
                summary="Developer-facing index of binding slice and runtime contracts.",
                contract_type="governance_index",
                layer="governance",
                status="active",
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=NORMATIVE_INDEX,
                source_of_truth=True,
                confidence=conf,
                discovery_reason="A: explicit governance index path + normative vocabulary in prose",
                tags=["slice", "navigation", "normative"],
            )
        )

    # A2 — OpenAPI (machine API contract)
    if p_openapi.is_file():
        head = _read_head(p_openapi, max_bytes=8000)
        conf = 0.94 if "openapi" in head.lower() else 0.75
        api_ver = read_openapi_version_from_file(p_openapi)
        impl: list[str] = []
        if (repo / "backend").is_dir():
            impl.append("backend/")
        proj_as: list[str] = []
        master_col = repo / "postman" / "WorldOfShadows_Complete_OpenAPI.postman_collection.json"
        if master_col.is_file():
            proj_as.append("postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json")
        add(
            _contract(
                cid="CTR-API-OPENAPI-001",
                title="Public HTTP API (OpenAPI 3)",
                summary="Declared REST surface for backend integration and tooling.",
                contract_type="api_schema",
                layer="api",
                status="active",
                version=api_ver,
                authority_level="normative",
                anchor_kind="machine_schema",
                anchor_location=openapi_default,
                source_of_truth=True,
                confidence=conf,
                discovery_reason="A: canonical OpenAPI document under docs/api/",
                tags=["http", "openapi", "backend"],
                implemented_by=impl,
                projected_as=proj_as,
            )
        )

    # A2b — Curated runtime/MVP spine (bounded, evidence-attached, higher priority than generic scans)
    curated_contracts, curated_projections, curated_relations, _curated_conflicts, _curated_families = build_runtime_mvp_spine(repo)
    curated_anchor_locations = {c.anchor_location for c in curated_contracts}
    for c in curated_contracts:
        add(c)
    projections.extend(curated_projections)
    relations.extend(curated_relations)

    # A3 — ADRs (canonical docs/ADR)
    # Only ADRs under the canonical `docs/ADR` directory are treated as active
    # contract anchors. Legacy ADR locations remain visible to ADR governance
    # tools, but are skipped here so the discovery inventory reflects the
    # repository rule that ADRs live in `docs/ADR`.
    for adr in iter_adr_markdown_paths(repo):
        if len(contracts) >= max_contracts:
            break
        rel = _safe_rel(adr, repo)
        if rel in curated_anchor_locations:
            continue
        # Skip legacy ADR locations; enforce canonical ADR home for discovery.
        if not rel.startswith("docs/ADR/"):
            continue
        head = _read_head(adr)
        st_raw = adr_declared_status(head)
        adr_status = _adr_contract_status(st_raw)
        conf = 0.9 + _marker_boost(head)
        slug = adr.stem.upper().replace("-", "_").replace(".", "_")
        location_reason = "docs/ADR"
        add(
            _contract(
                cid=f"CTR-ADR-{slug[:24]}",
                title=f"ADR: {adr.stem}",
                summary="Architecture decision record with governance force when accepted.",
                contract_type="adr",
                layer="governance",
                status=adr_status,
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=rel,
                source_of_truth=True,
                confidence=min(0.98, conf),
                discovery_reason=f"A: ADR filename pattern under {location_reason}",
                tags=["adr", "architecture"],
                notes=f"adr_status_line={st_raw}" if st_raw != "unknown" else "",
            )
        )

    # B2 — Operations runbook (operator contract surface)
    p_ops = repo / "docs" / "operations" / "OPERATIONAL_GOVERNANCE_RUNTIME.md"
    if p_ops.is_file() and len(contracts) < max_contracts:
        head = _read_head(p_ops)
        conf = 0.78 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-OPS-RUNTIME-001",
                title="Operational governance runtime (runbook)",
                summary="Operator-facing procedures and guarantees for runtime governance controls.",
                contract_type="operational_runbook",
                layer="operations",
                status="active",
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=_safe_rel(p_ops, repo),
                source_of_truth=True,
                confidence=min(0.9, conf),
                discovery_reason="B: explicit operations markdown under docs/operations/",
                tags=["operations", "operator"],
                owner_or_area="operations",
            )
        )

    # B3 — Shared JSON schemas (cross-boundary data contracts, capped at two files)
    schema_dir = repo / "schemas"
    if schema_dir.is_dir():
        schema_added = 0
        for sf in sorted(schema_dir.glob("*.json")):
            if len(contracts) >= max_contracts or schema_added >= 2:
                break
            rel = _safe_rel(sf, repo)
            stem = hashlib.sha256(rel.encode()).hexdigest()[:10].upper()
            add(
                _contract(
                    cid=f"CTR-SCHEMA-{stem}",
                    title=f"JSON schema: {sf.name}",
                    summary="Shared machine-readable schema constraining data exchanged across components.",
                    contract_type="json_schema",
                    layer="implementation",
                    status="active",
                    version="unversioned",
                    authority_level="normative",
                    anchor_kind="machine_schema",
                    anchor_location=rel,
                    source_of_truth=True,
                    confidence=0.74,
                    discovery_reason="B: top-level schemas/*.json with bounded scan (max 2 files per pass ceiling)",
                    tags=["schema", "data-contract"],
                )
            )
            schema_added += 1

    # A4a — Postmanify sync procedure (projection / regeneration contract)
    p_postmanify_task = repo / POSTMANIFY_SYNC_TASK
    if p_postmanify_task.is_file() and len(contracts) < max_contracts:
        head = _read_head(p_postmanify_task)
        conf = 0.86 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-POSTMANIFY-TASK-001",
                title="Postmanify sync task (OpenAPI → Postman)",
                summary="Procedure for regenerating Postman collections and manifest from the canonical OpenAPI anchor.",
                contract_type="suite_handoff",
                layer="workflow",
                status="active",
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=POSTMANIFY_SYNC_TASK,
                source_of_truth=True,
                confidence=min(0.94, conf),
                discovery_reason="A: postmanify task markdown under fy-suite (explicit OpenAPI linkage expected in prose)",
                tags=["postmanify", "openapi", "projection"],
                owner_or_area="platform",
                derived_from=[openapi_default],
            )
        )

    # A4b — Docify documentation check task (AST audit contract)
    p_docify_task = repo / DOCIFY_DOCUMENTATION_CHECK_TASK
    if p_docify_task.is_file() and len(contracts) < max_contracts:
        head = _read_head(p_docify_task)
        conf = 0.84 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-DOCIFY-TASK-001",
                title="Docify documentation check task",
                summary="Procedure and inputs for repository documentation quality audits (Python/docstring drift).",
                contract_type="suite_handoff",
                layer="documentation",
                status="active",
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=DOCIFY_DOCUMENTATION_CHECK_TASK,
                source_of_truth=True,
                confidence=min(0.93, conf),
                discovery_reason="A: docify governance task markdown under fy-suite",
                tags=["docify", "documentation"],
                owner_or_area="platform",
            )
        )

    # A4 — Despaghettify setup (explicit machine + prose contract)
    p_setup = repo / DESPAG_SETUP
    if p_setup.is_file():
        head = _read_head(p_setup)
        conf = 0.93 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-DESPAG-SETUP-001",
                title="Despaghettify spaghetti setup (normative)",
                summary="Numeric triggers and governance rules for structural execution hub.",
                contract_type="workflow_governance",
                layer="governance",
                status="active",
                version="unversioned",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=DESPAG_SETUP,
                source_of_truth=True,
                confidence=min(0.98, conf),
                discovery_reason="A: explicit canonical / normative sections in spaghetti-setup.md",
                tags=["despaghettify", "structure"],
                documented_in=[DESPAG_SETUP],
            )
        )

    # B1 — GitHub workflows (operational workflow contracts)
    wf_dir = repo / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.yml"))[:2]:
            if len(contracts) >= max_contracts:
                break
            rel = _safe_rel(wf, repo)
            head = _read_head(wf, max_bytes=12_000)
            conf = 0.68 + (0.05 if "workflow_dispatch" in head else 0.0)
            add(
                _contract(
                    cid=f"CTR-WF-{wf.stem.upper()[:20]}",
                    title=f"CI workflow: {wf.name}",
                    summary="Automation contract for verification gates and release hygiene.",
                    contract_type="ci_workflow",
                    layer="workflow",
                    status="active",
                    version="unversioned",
                    authority_level="verification",
                    anchor_kind="workflow_definition",
                    anchor_location=rel,
                    source_of_truth=True,
                    confidence=min(0.89, conf),
                    discovery_reason="B: structural workflow definition under .github/workflows/",
                    tags=["ci", "verification"],
                    owner_or_area="platform",
                )
            )

    # C — Projections: Postman manifest + collections are derived from OpenAPI
    p_mf = repo / POSTMAN_MANIFEST
    openapi_present = p_openapi.is_file()
    if p_mf.is_file() and openapi_present:
        try:
            manifest = json.loads(p_mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        openapi_rel = str(manifest.get("openapi_path", "")).replace("\\", "/")
        projections.append(
            ProjectionRecord(
                id="PRJ-POSTMANIFY-MANIFEST-001",
                title="Postmanify generation manifest",
                path=POSTMAN_MANIFEST,
                audience="developer",
                mode="specialist",
                source_contract_id="CTR-API-OPENAPI-001",
                anchor_location=openapi_rel or openapi_default,
                authoritative=False,
                confidence=0.95,
                evidence="postmanify-manifest.json records openapi_path and openapi_sha256",
                contract_version_ref=str(manifest.get("openapi_sha256", ""))[:16],
            )
        )
        relations.append(
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-POSTMANIFY-MANIFEST-001",
                target_id="CTR-API-OPENAPI-001",
                evidence="Manifest openapi_path binds generation input",
                confidence=0.95,
            )
        )
        master = str(manifest.get("master_collection", "")).replace("\\", "/")
        if master:
            projections.append(
                ProjectionRecord(
                    id="PRJ-POSTMAN-MASTER-001",
                    title="Postman master collection (OpenAPI projection)",
                    path=master,
                    audience="developer",
                    mode="specialist",
                    source_contract_id="CTR-API-OPENAPI-001",
                    anchor_location=openapi_default,
                    authoritative=False,
                    confidence=0.9,
                    evidence="Generated by postmanify from OpenAPI",
                    contract_version_ref=str(manifest.get("openapi_sha256", ""))[:16],
                )
            )
            relations.append(
                RelationEdge(
                    relation="projects",
                    source_id="PRJ-POSTMAN-MASTER-001",
                    target_id="CTR-API-OPENAPI-001",
                    evidence="Postmanify emits collection from same OpenAPI revision fingerprint",
                    confidence=0.9,
                )
            )

    # C — Easy / start-here docs as audience projections of normative index
    anchor_norm = "CTR-NORM-INDEX-001"
    if not has_normative_index:
        anchor_norm = ""
    for folder in (repo / "docs" / "easy", repo / "docs" / "start-here"):
        if not folder.is_dir() or not anchor_norm:
            continue
        for md in sorted(folder.glob("*.md"))[:12]:
            rel = _safe_rel(md, repo)
            digest = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:10]
            pid = f"PRJ-EASY-{digest}"
            projections.append(
                ProjectionRecord(
                    id=pid,
                    title=f"Audience doc: {md.name}",
                    path=rel,
                    audience="stakeholder" if "easy" in rel else "developer",
                    mode="easy" if "easy" in rel else "ai_reading",
                    source_contract_id=anchor_norm,
                    anchor_location=NORMATIVE_INDEX,
                    authoritative=False,
                    confidence=0.62,
                    evidence="Path under docs/easy or docs/start-here; treated as projection hub by policy",
                )
            )
            relations.append(
                RelationEdge(
                    relation="documents",
                    source_id=pid,
                    target_id=anchor_norm,
                    evidence="House rule: easy/start-here layers summarise normative index entries",
                    confidence=0.55,
                )
            )

    # Self — Contractify suite charter (documentation anchor)
    self_readme = repo / "'fy'-suites" / "contractify" / "README.md"
    if self_readme.is_file() and len(contracts) < max_contracts:
        head = _read_head(self_readme)
        conf = 0.88 + _marker_boost(head)
        add(
            _contract(
                cid="CTR-CONTRACTIFY-SELF-001",
                title="Contractify suite charter",
                summary="Defines suite scope, truth model, drift classes, and integration with sibling fy hubs.",
                contract_type="suite_charter",
                layer="governance",
                status="active",
                version="0.1.0",
                authority_level="normative",
                anchor_kind="document",
                anchor_location=_safe_rel(self_readme, repo),
                source_of_truth=True,
                confidence=min(0.95, conf),
                discovery_reason="Self-application: contractify/README.md describes suite obligations",
                tags=["contractify", "meta"],
                owner_or_area="platform",
            )
        )

    # Handoff edges (suite charter points consumers at normative index when present)
    if has_normative_index and any(c.id == "CTR-CONTRACTIFY-SELF-001" for c in contracts):
        relations.append(
            RelationEdge(
                relation="operationalizes",
                source_id="CTR-CONTRACTIFY-SELF-001",
                target_id="CTR-NORM-INDEX-001",
                evidence="Suite README instructs readers to anchor product contracts in normative index",
                confidence=0.55,
            )
        )

    return contracts, projections, relations


def projection_backref_ok(md_path: Path, *, normative_fragment: str = "normative-contracts-index") -> tuple[bool, str]:
    """Heuristic C-tier: audience markdown should link back to normative
    index or carry machine marker.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        md_path: Filesystem path to the file or directory being
            processed.
        normative_fragment: Primary normative fragment used by this
            step.

    Returns:
        tuple[bool, str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    text = _read_head(md_path, max_bytes=120_000)
    if "contractify-projection:" in text:
        return True, "explicit contractify-projection marker"
    if normative_fragment in text.replace("\\", "/"):
        return True, "markdown link or path mention to normative contracts index"
    return False, "missing explicit back-reference to normative index (heuristic)"
