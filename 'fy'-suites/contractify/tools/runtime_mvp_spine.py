"""Curated runtime/MVP contract spine attachments for World of Shadows.

This module promotes the high-value runtime/MVP contract family into explicit,
related, evidence-attached Contractify records without broad repository mining.
The inventory is intentionally bounded to avoid graph explosion.
"""
from __future__ import annotations

from pathlib import Path

from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord, RelationEdge


RUNTIME_AUTHORITY = "runtime_authority"
SLICE_NORMATIVE = "slice_normative"
IMPLEMENTATION_EVIDENCE = "implementation_evidence"
VERIFICATION_EVIDENCE = "verification_evidence"
PROJECTION_LOW = "projection_low"

def _first_existing(repo: Path, *rel_paths: str) -> str:
    for rel in rel_paths:
        if rel and (repo / rel).is_file():
            return rel.replace("\\", "/")
    return ""


def _ownership_input(repo: Path) -> str:
    return _first_existing(repo, "validation/fy_inputs/contractify_vocabulary_ownership.json")


def _adr0001(repo: Path) -> str:
    return _first_existing(repo, "docs/ADR/adr-0001-runtime-authority-in-world-engine.md", "docs/governance/adr-0001-runtime-authority-in-world-engine.md")


def _adr0002(repo: Path) -> str:
    return _first_existing(repo, "docs/ADR/adr-0002-backend-session-surface-quarantine.md", "docs/governance/adr-0002-backend-session-surface-quarantine.md")


def _adr0003(repo: Path) -> str:
    return _first_existing(repo, "docs/ADR/adr-0003-scene-identity-canonical-surface.md", "docs/governance/adr-0003-scene-identity-canonical-surface.md")

PRECEDENCE_RULES: list[dict[str, object]] = [
    {
        "tier": RUNTIME_AUTHORITY,
        "rank": 1,
        "summary": "Highest-order runtime authority and boundary contracts. These outrank slice detail, implementation observations, and projections when authority clashes are reviewed.",
    },
    {
        "tier": SLICE_NORMATIVE,
        "rank": 2,
        "summary": "Binding MVP / slice contracts and accepted slice-scoped ADRs. These govern GoC behavior beneath the runtime authority layer.",
    },
    {
        "tier": IMPLEMENTATION_EVIDENCE,
        "rank": 3,
        "summary": "Observed code surfaces that embody or operationalize contracts but do not replace normative authority.",
    },
    {
        "tier": VERIFICATION_EVIDENCE,
        "rank": 4,
        "summary": "Test and verification surfaces that support claims about implementation and documented paths.",
    },
    {
        "tier": PROJECTION_LOW,
        "rank": 5,
        "summary": "Lower-weight audience projections and convenience summaries. Useful for navigation, never equal to runtime authority or slice contracts.",
    },
]


def _existing(repo: Path, *rels: str) -> list[str]:
    out: list[str] = []
    for rel in rels:
        rel = rel.replace("\\", "/")
        if (repo / rel).is_file():
            out.append(rel)
    return out


def _has_current_repo_evidence(repo: Path, finding: ConflictFinding) -> bool:
    """Return true when a manual finding has both authority and observed evidence.

    The runtime/MVP spine is also used in hermetic and partial checkouts. In
    those layouts, keeping manual World of Shadows follow-up findings visible
    without the supporting files creates false blockers.
    """
    normative = [
        rel
        for rel in finding.normative_sources
        if rel and (repo / rel).is_file()
    ]
    observed = [
        rel
        for rel in finding.observed_or_projection_sources
        if rel and (repo / rel).is_file()
    ]
    return len(normative) >= 2 and bool(observed)


def _contract(
    *,
    cid: str,
    title: str,
    summary: str,
    contract_type: str,
    layer: str,
    authority_level: str,
    anchor_kind: str,
    anchor_location: str,
    precedence_tier: str,
    tags: list[str],
    owner_or_area: str,
    scope: str,
    source_of_truth: bool = True,
    status: str = "active",
    version: str = "unversioned",
    confidence: float = 0.95,
    derived_from: list[str] | None = None,
    implemented_by: list[str] | None = None,
    validated_by: list[str] | None = None,
    documented_in: list[str] | None = None,
    projected_as: list[str] | None = None,
    notes: str = "",
) -> ContractRecord:
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
        audiences=["developer", "architect"],
        modes=["specialist"],
        scope=scope,
        owner_or_area=owner_or_area,
        confidence=confidence,
        drift_signals=[],
        notes=notes,
        last_verified="",
        change_risk="unknown",
        tags=tags,
        discovery_reason="Curated runtime/MVP spine attachment inventory.",
        precedence_tier=precedence_tier,
    )


def _projection(
    *,
    pid: str,
    title: str,
    path: str,
    source_contract_id: str,
    audience: str,
    mode: str,
    evidence: str,
    anchor_location: str,
    confidence: float = 0.82,
) -> ProjectionRecord:
    return ProjectionRecord(
        id=pid,
        title=title,
        path=path,
        audience=audience,
        mode=mode,
        source_contract_id=source_contract_id,
        anchor_location=anchor_location,
        authoritative=False,
        confidence=confidence,
        evidence=evidence,
        precedence_tier=PROJECTION_LOW,
    )


def _path_target_id(path_to_id: dict[str, str], rel: str) -> str:
    rel = rel.replace("\\", "/")
    return path_to_id.get(rel, f"ART:{rel}")


def _field_edges(records: list[ContractRecord], path_to_id: dict[str, str]) -> list[RelationEdge]:
    out: list[RelationEdge] = []
    for rec in records:
        for dep in rec.derived_from:
            out.append(
                RelationEdge(
                    relation="derives_from",
                    source_id=rec.id,
                    target_id=dep,
                    evidence=f"{rec.anchor_location} declares derived_from={dep} in curated runtime/MVP spine metadata.",
                    confidence=0.96,
                )
            )
        for rel in rec.implemented_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="implemented_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to implementation surface {rel}.",
                    confidence=0.93,
                )
            )
            out.append(
                RelationEdge(
                    relation="implements",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Implementation surface {rel} materially embodies {rec.anchor_location}.",
                    confidence=0.93,
                )
            )
        for rel in rec.validated_by:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="validated_by",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment links {rec.anchor_location} to verification surface {rel}.",
                    confidence=0.91,
                )
            )
            out.append(
                RelationEdge(
                    relation="validates",
                    source_id=tid,
                    target_id=rec.id,
                    evidence=f"Verification surface {rel} is cited as direct evidence for {rec.anchor_location}.",
                    confidence=0.91,
                )
            )
        for rel in rec.documented_in:
            tid = _path_target_id(path_to_id, rel)
            out.append(
                RelationEdge(
                    relation="documented_in",
                    source_id=rec.id,
                    target_id=tid,
                    evidence=f"Curated attachment records {rel} as supporting documentation for {rec.anchor_location}.",
                    confidence=0.86,
                )
            )
        for rel in rec.projected_as:
            out.append(
                RelationEdge(
                    relation="projected_as",
                    source_id=rec.id,
                    target_id=f"PRJPATH:{rel}",
                    evidence=f"Curated attachment records {rel} as a lower-weight projection of {rec.anchor_location}.",
                    confidence=0.8,
                )
            )
    return out


def build_runtime_mvp_spine(
    repo: Path,
) -> tuple[list[ContractRecord], list[ProjectionRecord], list[RelationEdge], list[ConflictFinding], dict[str, list[str]]]:
    repo = repo.resolve()
    contracts: list[ContractRecord] = []
    path_to_id: dict[str, str] = {}

    def add(rec: ContractRecord) -> None:
        if not (repo / rec.anchor_location).is_file():
            return
        contracts.append(rec)
        path_to_id[rec.anchor_location] = rec.id

    # High-order runtime authority + ADRs.
    add(
        _contract(
            cid="CTR-ADR-0001-RUNTIME-AUTHORITY",
            title="ADR-0001: Runtime authority in world-engine",
            summary="Accepted runtime authority decision: world-engine owns authoritative live narrative execution.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0001(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "world-engine"],
            owner_or_area="architecture",
            scope="runtime authority boundary",
            implemented_by=_existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
            ),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/dev/architecture/runtime-authority-and-session-lifecycle.md",
                _ownership_input(repo),
            ),
            projected_as=_existing(repo, "docs/dev/onboarding.md"),
            notes="Authority record outranks slice-level contracts if host ownership claims conflict.",
        )
    )
    add(
        _contract(
            cid="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
            title="ADR-0002: Backend session / transitional runtime quarantine",
            summary="Accepted quarantine/retirement policy for backend-local session and runtime-shaped surfaces.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0002(repo),
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "adr", "backend", "transitional"],
            owner_or_area="architecture",
            scope="backend transitional session surfaces",
            implemented_by=_existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=_existing(
                repo,
                "backend/tests/test_session_routes.py",
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                _ownership_input(repo),
            ),
            projected_as=_existing(repo, "docs/dev/onboarding.md"),
            notes="Quarantine record governs compatibility and retirement, not live session authority.",
        )
    )
    add(
        _contract(
            cid="CTR-ADR-0003-SCENE-IDENTITY",
            title="ADR-0003: Single canonical scene identity surface",
            summary="Accepted slice ADR choosing one owned GoC scene-identity surface across compile, AI guidance, and commit.",
            contract_type="adr",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location=_adr0003(repo),
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:scene_identity", "adr", "goc"],
            owner_or_area="ai_stack",
            scope="GoC scene identity seam",
            implemented_by=_existing(
                repo,
                "ai_stack/goc_scene_identity.py",
                "ai_stack/goc_yaml_authority.py",
            ),
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(
                repo,
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
                _first_existing(repo, "docs/ADR/README.md", "docs/governance/README.md"),
            ),
            notes="Slice-specific ADR below runtime authority tier.",
        )
    )

    # First-class normative docs.
    add(
        _contract(
            cid="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            title="Runtime authority and state flow",
            summary="Consolidated runtime host/state progression contract for live play and transitional backend surfaces.",
            contract_type="runtime_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/runtime-authority-and-state-flow.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "runtime", "world-engine"],
            owner_or_area="world-engine",
            scope="runtime lifecycle and state authority",
            derived_from=["CTR-ADR-0001-RUNTIME-AUTHORITY"],
            implemented_by=_existing(
                repo,
                "world-engine/app/story_runtime/manager.py",
                "world-engine/app/api/http.py",
                "backend/app/runtime/session_store.py",
            ),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                _adr0001(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=_existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/runtime-interactions-player-visible.md",
            ),
        )
    )
    add(
        _contract(
            cid="CTR-BACKEND-RUNTIME-CLASSIFICATION",
            title="Backend runtime classification",
            summary="Classification contract separating backend-local volatile surfaces from authoritative runtime execution.",
            contract_type="runtime_boundary_contract",
            layer="architecture",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/architecture/backend-runtime-classification.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "backend", "classification"],
            owner_or_area="backend",
            scope="backend transitional runtime boundaries",
            implemented_by=_existing(
                repo,
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
                "backend/app/api/v1/world_engine_console_routes.py",
            ),
            validated_by=_existing(
                repo,
                "backend/tests/test_session_routes.py",
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                _adr0001(repo),
                _adr0002(repo),
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
            projected_as=_existing(repo, "docs/technical/architecture/service-boundaries.md"),
        )
    )
    add(
        _contract(
            cid="CTR-CANONICAL-RUNTIME-CONTRACT",
            title="Canonical Runtime Contract (Nested Run V1)",
            summary="Binding producer/consumer payload contract for play-service run create/detail/terminate envelopes.",
            contract_type="producer_consumer_contract",
            layer="api",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/architecture/canonical_runtime_contract.md",
            precedence_tier=RUNTIME_AUTHORITY,
            tags=["family:runtime_authority", "api", "payload", "nested-run-v1"],
            owner_or_area="backend",
            scope="world-engine HTTP to backend consumer seam",
            implemented_by=_existing(
                repo,
                "world-engine/app/api/http.py",
                "backend/app/services/game_service.py",
            ),
            validated_by=_existing(
                repo,
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
            ),
        )
    )
    add(
        _contract(
            cid="CTR-PLAYER-INPUT-INTERPRETATION",
            title="Player Input Interpretation Contract",
            summary="Structured interpretation contract for raw player text, explicit commands, ambiguity, and delivery hints.",
            contract_type="runtime_input_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/runtime/player_input_interpretation_contract.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:input_turn", "input", "runtime"],
            owner_or_area="story_runtime_core",
            scope="authoritative and preview interpretation of player input",
            implemented_by=_existing(
                repo,
                "story_runtime_core/input_interpreter.py",
                "world-engine/app/story_runtime/manager.py",
                "backend/app/api/v1/session_routes.py",
            ),
            validated_by=_existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
                "docs/technical/architecture/architecture-overview.md",
            ),
            projected_as=_existing(repo, "docs/start-here/how-ai-fits-the-platform.md"),
        )
    )
    add(
        _contract(
            cid="CTR-GOC-VERTICAL-SLICE",
            title="GoC Vertical Slice Contract",
            summary="Primary MVP vertical-slice contract defining GoC scope, YAML authority, and runtime bridge expectations.",
            contract_type="slice_contract",
            layer="governance",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "slice", "mvp"],
            owner_or_area="product",
            scope="GoC MVP slice",
            implemented_by=_existing(
                repo,
                "ai_stack/goc_yaml_authority.py",
                "ai_stack/goc_scene_identity.py",
            ),
            validated_by=_existing(
                repo,
                "tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
                "tests/smoke/test_repository_documented_paths_resolve.py",
            ),
            documented_in=_existing(
                repo,
                "docs/dev/onboarding.md",
                "docs/user/god-of-carnage-player-guide.md",
            ),
            projected_as=_existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/admin/publishing-and-module-activation.md",
            ),
        )
    )
    add(
        _contract(
            cid="CTR-GOC-CANONICAL-TURN",
            title="GoC Canonical Turn Contract",
            summary="Binding GoC turn envelope schema for validation, commit, diagnostics, and review.",
            contract_type="turn_contract",
            layer="runtime",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "turn", "mvp"],
            owner_or_area="world-engine",
            scope="GoC authoritative turn envelope",
            derived_from=["CTR-GOC-VERTICAL-SLICE"],
            implemented_by=_existing(repo, "world-engine/app/story_runtime/manager.py"),
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/user/god-of-carnage-player-guide.md",
                "docs/dev/onboarding.md",
            ),
            projected_as=_existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
        )
    )
    add(
        _contract(
            cid="CTR-GOC-GATE-SCORING",
            title="GoC Gate Scoring Policy",
            summary="Gate/scoring policy for GoC evaluation, fallback classification, and experience acceptance evidence.",
            contract_type="gate_policy",
            layer="policy",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:goc", "gate", "scoring"],
            owner_or_area="qa",
            scope="GoC gate scoring and evidence policy",
            validated_by=_existing(repo, "tests/experience_scoring_cli/test_experience_score_matrix_cli.py"),
            documented_in=_existing(
                repo,
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
                "docs/audit/evidence_artifact_mapping_table.md",
            ),
            projected_as=_existing(repo, "docs/goc_evidence_templates/README.md"),
        )
    )
    add(
        _contract(
            cid="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            title="Writers’ Room and publishing flow",
            summary="Backend-first Writers’ Room review/publishing workflow with a bounded retrieval overlap seam; AI outputs remain recommendation-only until human/backend publishing governance applies changes.",
            contract_type="content_workflow_contract",
            layer="workflow",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/content/writers-room-and-publishing-flow.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:publish_rag", "writers_room", "publishing"],
            owner_or_area="backend",
            scope="review and publishing governance",
            implemented_by=_existing(repo, "backend/app/api/v1/writers_room_routes.py"),
            validated_by=_existing(repo, "backend/tests/writers_room/test_writers_room_routes.py"),
            documented_in=_existing(
                repo,
                "docs/admin/publishing-and-module-activation.md",
                "governance/V24_WRITERS_ROOM_RAG_OVERLAP_LEDGER.md",
            ),
            projected_as=_existing(repo, "docs/admin/publishing-and-module-activation.md"),
            notes="Intentional overlap with RAG is limited to retrieval_context_provider and context_pack_assembly support; publish_authority, canonical promotion, and runtime truth remain separate.",
        )
    )
    add(
        _contract(
            cid="CTR-RAG-GOVERNANCE",
            title="RAG governance",
            summary="Retrieval governance contract separating retrieved context from authored canon and committed runtime state, including a bounded Writers’ Room overlap seam at retrieval/context-pack support only.",
            contract_type="ai_retrieval_contract",
            layer="ai_machine",
            authority_level="normative",
            anchor_kind="document",
            anchor_location="docs/technical/ai/RAG.md",
            precedence_tier=SLICE_NORMATIVE,
            tags=["family:publish_rag", "rag", "ai"],
            owner_or_area="ai_stack",
            scope="retrieval domains, governance lanes, and context assembly",
            implemented_by=_existing(
                repo,
                "ai_stack/rag.py",
                "world-engine/app/story_runtime/manager.py",
            ),
            validated_by=_existing(
                repo,
                "world-engine/tests/test_story_runtime_api.py",
                "ai_stack/tests/test_rag.py",
            ),
            documented_in=_existing(
                repo,
                "docs/ai/ai_system_in_world_of_shadows.md",
                "docs/technical/integration/LangGraph.md",
                "docs/technical/integration/LangChain.md",
                "governance/V24_WRITERS_ROOM_RAG_OVERLAP_LEDGER.md",
                "docs/technical/content/writers-room-and-publishing-flow.md",
            ),
            projected_as=_existing(repo, "docs/ai/ai_system_in_world_of_shadows.md"),
            notes="Writers’ Room support is limited to retrieval_context_provider and context_pack_assembly; retrieval output remains recommendation/context support and not publish_authority or runtime truth.",
        )
    )
    add(
        _contract(
            cid="CTR-TESTING-ORCHESTRATION",
            title="Test orchestration and suite runner",
            summary="Repository-level testing governance anchor describing orchestrated suite execution and environment preflight expectations.",
            contract_type="test_governance",
            layer="testing",
            authority_level="verification",
            anchor_kind="document",
            anchor_location="tests/TESTING.md",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "testing", "orchestration"],
            owner_or_area="qa",
            scope="repository-wide test orchestration",
            implemented_by=_existing(repo, "tests/run_tests.py"),
            documented_in=_existing(repo, "docs/dev/testing/test-pyramid-and-suite-map.md"),
            projected_as=_existing(repo, "docs/testing/README.md"),
            notes="Verification governance anchor, not a product/runtime authority contract.",
        )
    )

    # Mandatory implementation / evidence surfaces.
    add(
        _contract(
            cid="OBS-WE-STORY-RUNTIME-MANAGER",
            title="StoryRuntimeManager implementation surface",
            summary="Observed authoritative runtime manager for story sessions, turn execution, retrieval wiring, and diagnostics.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/story_runtime/manager.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime manager code",
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/ai/RAG.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-WE-HTTP-API",
            title="World-engine HTTP API surface",
            summary="Observed FastAPI play-service surface for runs and story sessions.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="world-engine/app/api/http.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "api"],
            owner_or_area="world-engine",
            scope="play-service API code",
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-BE-SESSION-ROUTES",
            title="Backend session routes surface",
            summary="Observed backend session API surface explicitly labeled non-authoritative and partly world-engine-bridged.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/session_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend"],
            owner_or_area="backend",
            scope="backend transitional session routes",
            validated_by=_existing(
                repo,
                "backend/tests/test_session_routes.py",
                "backend/tests/test_session_api_contracts.py",
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-BE-SESSION-STORE",
            title="Backend session store surface",
            summary="Observed volatile in-memory runtime session registry retained for tests, MCP, and transitional operator flows.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/runtime/session_store.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "transitional"],
            owner_or_area="backend",
            scope="backend volatile session registry",
            validated_by=_existing(
                repo,
                "backend/tests/runtime/test_session_store.py",
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-BE-SESSION-SERVICE",
            title="Backend session service surface",
            summary="Observed session service bridge for backend-local SessionState bootstrap and deferred W3.2 behavior.",
            contract_type="implementation_surface",
            layer="implementation",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/services/session_service.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "transitional"],
            owner_or_area="backend",
            scope="backend session service bridge",
            validated_by=_existing(
                repo,
                "backend/tests/services/test_session_service.py",
                "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
            ),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES",
            title="Backend world-engine console routes",
            summary="Observed admin/JWT proxy surface for controlled play-service observation and operations.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/world_engine_console_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "admin"],
            owner_or_area="backend",
            scope="admin world-engine console routes",
            validated_by=_existing(repo, "tests/smoke/test_backend_transitional_retirement_surface_contracts.py"),
            documented_in=_existing(
                repo,
                "docs/technical/architecture/backend-runtime-classification.md",
                _adr0002(repo),
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-BE-WRITERS-ROOM-ROUTES",
            title="Backend Writers’ Room routes",
            summary="Observed backend review/decision route surface for Writers’ Room workflow execution.",
            contract_type="implementation_surface",
            layer="workflow",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/api/v1/writers_room_routes.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:publish_rag", "implementation", "backend"],
            owner_or_area="backend",
            scope="writers-room review routes",
            documented_in=_existing(repo, "docs/technical/content/writers-room-and-publishing-flow.md"),
        )
    )
    add(
        _contract(
            cid="OBS-CORE-INPUT-INTERPRETER",
            title="Shared input interpreter surface",
            summary="Observed implementation of structured natural-language and command interpretation.",
            contract_type="implementation_surface",
            layer="runtime",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="story_runtime_core/input_interpreter.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:input_turn", "implementation", "core"],
            owner_or_area="story_runtime_core",
            scope="input interpretation logic",
            validated_by=_existing(
                repo,
                "story_runtime_core/tests/test_input_interpreter.py",
                "world-engine/tests/test_story_runtime_api.py",
            ),
            documented_in=_existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )
    add(
        _contract(
            cid="OBS-AI-GOC-SCENE-IDENTITY",
            title="GoC scene identity implementation surface",
            summary="Observed single owned scene identity mapping for GoC guidance and escalation vocabulary.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/goc_scene_identity.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:scene_identity", "implementation", "ai_stack"],
            owner_or_area="ai_stack",
            scope="GoC scene identity mapping",
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(repo, "docs/governance/adr-0003-scene-identity-canonical-surface.md"),
        )
    )
    add(
        _contract(
            cid="OBS-AI-GOC-YAML-AUTHORITY",
            title="GoC YAML authority surface",
            summary="Observed YAML authority loader/re-export surface consuming the canonical scene identity module.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/goc_yaml_authority.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:scene_identity", "implementation", "ai_stack"],
            owner_or_area="ai_stack",
            scope="GoC YAML authority helpers",
            validated_by=_existing(repo, "ai_stack/tests/test_goc_scene_identity.py"),
            documented_in=_existing(
                repo,
                "docs/governance/adr-0003-scene-identity-canonical-surface.md",
                "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
            ),
        )
    )
    add(
        _contract(
            cid="OBS-AI-RAG",
            title="RAG implementation surface",
            summary="Observed retrieval corpus, request, ranking, and governance implementation for runtime and Writers’ Room callers.",
            contract_type="implementation_surface",
            layer="ai_machine",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/rag.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:publish_rag", "implementation", "ai_stack", "rag"],
            owner_or_area="ai_stack",
            scope="retrieval implementation",
            validated_by=_existing(repo, "world-engine/tests/test_story_runtime_api.py"),
            documented_in=_existing(repo, "docs/technical/ai/RAG.md"),
        )
    )
    add(
        _contract(
            cid="OBS-BE-GAME-SERVICE",
            title="Backend game service seam",
            summary="Observed backend consumer/proxy seam for world-engine run and story-session APIs.",
            contract_type="implementation_surface",
            layer="api",
            authority_level="observed",
            anchor_kind="code_boundary",
            anchor_location="backend/app/services/game_service.py",
            precedence_tier=IMPLEMENTATION_EVIDENCE,
            tags=["family:runtime_authority", "implementation", "backend", "consumer"],
            owner_or_area="backend",
            scope="world-engine consumer bridge",
            documented_in=_existing(
                repo,
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/architecture/backend-runtime-classification.md",
            ),
        )
    )
    add(
        _contract(
            cid="VER-TEST-RUNNER-CLI",
            title="Repository pytest runner implementation",
            summary="Observed multi-suite pytest orchestrator used as the root verification launcher.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/run_tests.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "verification", "runner"],
            owner_or_area="qa",
            scope="test orchestration code",
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )
    add(
        _contract(
            cid="VER-AI-GOC-SCENE-IDENTITY-TEST",
            title="GoC scene identity contract tests",
            summary="Verification suite asserting canonical scene-id mapping and duplicate-definition protection for ADR-0003.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="ai_stack/tests/test_goc_scene_identity.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:scene_identity", "verification", "pytest"],
            owner_or_area="ai_stack",
            scope="scene identity verification",
            documented_in=_existing(
                repo,
                "docs/governance/adr-0003-scene-identity-canonical-surface.md",
                "docs/audit/repo_evidence_index.md",
            ),
        )
    )
    add(
        _contract(
            cid="VER-CORE-INPUT-INTERPRETER-TEST",
            title="Input interpreter contract tests",
            summary="Verification suite covering structured kind selection and runtime delivery hints for player input interpretation.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="story_runtime_core/tests/test_input_interpreter.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:input_turn", "verification", "pytest"],
            owner_or_area="story_runtime_core",
            scope="input interpretation verification",
            documented_in=_existing(repo, "docs/technical/runtime/player_input_interpretation_contract.md"),
        )
    )
    add(
        _contract(
            cid="VER-GOC-EXPERIENCE-SCORE-CLI-TEST",
            title="Experience score matrix CLI tests",
            summary="Verification suite for the G9 threshold validator and canonical six-scenario GoC experience matrix ordering/rules.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:goc", "verification", "g9"],
            owner_or_area="qa",
            scope="GoC gate scoring verification",
            documented_in=_existing(
                repo,
                "docs/audit/repo_evidence_index.md",
                "docs/audit/gate_G9_experience_acceptance_baseline.md",
            ),
        )
    )
    add(
        _contract(
            cid="VER-SMOKE-DOCUMENTED-PATHS",
            title="Repository documented paths smoke test",
            summary="Verification guard asserting high-visibility documented module/test paths resolve on disk.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="tests/smoke/test_repository_documented_paths_resolve.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:testing", "verification", "smoke"],
            owner_or_area="qa",
            scope="documented path existence guard",
            documented_in=_existing(repo, "docs/audit/repo_evidence_index.md"),
        )
    )
    add(
        _contract(
            cid="VER-BE-WORLD-ENGINE-CONSOLE-ROUTES-TEST",
            title="Backend world-engine console route tests",
            summary="Verification suite for admin console proxy authorization and world-engine bridge route behavior.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="backend/tests/test_world_engine_console_routes.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:runtime_authority", "verification", "backend"],
            owner_or_area="backend",
            scope="admin proxy verification",
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )
    add(
        _contract(
            cid="VER-WE-STORY-RUNTIME-API-TEST",
            title="World-engine story runtime API tests",
            summary="Verification suite for story-session lifecycle, retrieval fields, and interpreted-input behavior.",
            contract_type="verification_surface",
            layer="testing",
            authority_level="verification",
            anchor_kind="code_boundary",
            anchor_location="world-engine/tests/test_story_runtime_api.py",
            precedence_tier=VERIFICATION_EVIDENCE,
            tags=["family:runtime_authority", "verification", "world-engine"],
            owner_or_area="world-engine",
            scope="story runtime API verification",
            documented_in=_existing(repo, "tests/TESTING.md"),
        )
    )

    projections = [
        _projection(
            pid="PRJ-RUNTIME-AUTH-ONBOARDING",
            title="Developer onboarding runtime authority summary",
            path="docs/dev/onboarding.md",
            source_contract_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            audience="developer",
            mode="easy",
            evidence="Onboarding links runtime authority and GoC contract family as navigation surface.",
            anchor_location="docs/technical/runtime/runtime-authority-and-state-flow.md",
        )
        if (repo / "docs/dev/onboarding.md").is_file()
        else None,
        _projection(
            pid="PRJ-GOC-PLAYER-GUIDE",
            title="Player-facing GoC guide",
            path="docs/user/god-of-carnage-player-guide.md",
            source_contract_id="CTR-GOC-VERTICAL-SLICE",
            audience="user",
            mode="easy",
            evidence="Player guide summarizes the slice and turn contract family for a non-authority audience.",
            anchor_location="docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
        )
        if (repo / "docs/user/god-of-carnage-player-guide.md").is_file()
        else None,
        _projection(
            pid="PRJ-PUBLISHING-ADMIN-GUIDE",
            title="Admin publishing guide",
            path="docs/admin/publishing-and-module-activation.md",
            source_contract_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            audience="operator",
            mode="easy",
            evidence="Admin guide summarizes Writers’ Room / publishing flow for operational consumers.",
            anchor_location="docs/technical/content/writers-room-and-publishing-flow.md",
        )
        if (repo / "docs/admin/publishing-and-module-activation.md").is_file()
        else None,
        _projection(
            pid="PRJ-AI-SYSTEM-RAG-SUMMARY",
            title="AI system overview RAG summary",
            path="docs/ai/ai_system_in_world_of_shadows.md",
            source_contract_id="CTR-RAG-GOVERNANCE",
            audience="developer",
            mode="easy",
            evidence="AI system overview re-presents RAG and runtime authority concepts for cross-system navigation.",
            anchor_location="docs/technical/ai/RAG.md",
        )
        if (repo / "docs/ai/ai_system_in_world_of_shadows.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-README",
            title="API README projection",
            path="docs/api/README.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="easy",
            evidence="API README is governed as a projection-layer overview rather than a higher-order contract.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/README.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-REFERENCE",
            title="API reference projection",
            path="docs/api/REFERENCE.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="Human-readable backend reference remains a convenience projection of the OpenAPI/schema layer and validated route code.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/REFERENCE.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-POSTMAN-GUIDE",
            title="API Postman guide projection",
            path="docs/api/POSTMAN_COLLECTION.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="operator",
            mode="specialist",
            evidence="Postman guide is a lower-order operational projection and not a primary schema anchor.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/api/POSTMAN_COLLECTION.md").is_file()
        else None,
        _projection(
            pid="PRJ-API-EXPLORER-STRATEGY",
            title="OpenAPI and API explorer strategy projection",
            path="docs/dev/api/openapi-and-api-explorer-strategy.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="Strategy doc records current projection limits and future re-audit checks without becoming the canonical API contract.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "docs/dev/api/openapi-and-api-explorer-strategy.md").is_file()
        else None,
        _projection(
            pid="PRJ-POSTMAN-README",
            title="Postman README projection",
            path="postman/README.md",
            source_contract_id="CTR-API-OPENAPI-001",
            audience="developer",
            mode="specialist",
            evidence="Postman README explains generated collections as operational projections of the packaged OpenAPI artifact.",
            anchor_location="docs/api/openapi.yaml",
        )
        if (repo / "postman/README.md").is_file()
        else None,
    ]
    projections = [p for p in projections if p is not None]

    for prj in projections:
        path_to_id[prj.path] = prj.id

    relations = _field_edges(contracts, path_to_id)
    relations.extend(
        [
            RelationEdge(
                relation="refines",
                source_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The technical runtime authority page expands ADR-0001 into an operational ownership matrix and lifecycle narrative.",
                confidence=0.97,
            ),
            RelationEdge(
                relation="refines",
                source_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The backend classification page clarifies what ADR-0001 forbids inside Flask as live runtime authority.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="The classification document turns ADR-0002 quarantine language into concrete package/module labels.",
                confidence=0.96,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
                evidence="The nested-run producer/consumer contract assumes a single authoritative run host chosen by ADR-0001.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="The backend consumer rules in Nested Run V1 sit beside ADR-0002’s prohibition on treating backend-local session surfaces as equivalent runtime truth.",
                confidence=0.86,
            ),
RelationEdge(
    relation="refines",
    source_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
    target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
    evidence="ADR-0002 explicitly states that ADR-0001 remains the sole normative owner of runtime authority and narrows only backend session-surface quarantine and labeling under that model.",
    confidence=0.94,
),
RelationEdge(
    relation="depends_on",
    source_id="CTR-ADR-0003-SCENE-IDENTITY",
    target_id="CTR-ADR-0001-RUNTIME-AUTHORITY",
    evidence="ADR-0003 explicitly states that it does not define runtime authority and instead applies scene-identity continuity rules under ADR-0001.",
    confidence=0.93,
),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-GOC-GATE-SCORING",
                target_id="CTR-GOC-CANONICAL-TURN",
                evidence="Gate scoring references turn-envelope semantics and preview/productive classification from the canonical turn contract.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-GOC-GATE-SCORING",
                target_id="CTR-GOC-VERTICAL-SLICE",
                evidence="Gate scoring depends on the slice’s scope, vocabulary, and failure-mode boundaries.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="overlaps_with",
                source_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="The Writers’ Room workflow overlaps with RAG only at retrieval_context_provider and context_pack_assembly, while publish_authority, canonical promotion, and runtime committed truth remain separate.",
                confidence=0.9,
            ),
            RelationEdge(
                relation="overlaps_with",
                source_id="CTR-RAG-GOVERNANCE",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="RAG defines a Writers’ Room retrieval lane and context-pack support role, but remains subordinate to backend/admin publishing governance and world-engine runtime truth.",
                confidence=0.9,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-WE-STORY-RUNTIME-MANAGER",
                target_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                evidence="StoryRuntimeManager is named as the first code anchor on the runtime-authority page and wires runtime sessions, retrieval, and turn execution.",
                confidence=0.94,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-SESSION-ROUTES",
                target_id="CTR-BACKEND-RUNTIME-CLASSIFICATION",
                evidence="Session routes embody the backend-local quarantine by returning warnings and bridging to the world-engine for authoritative turns.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES",
                target_id="CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
                evidence="Admin console routes are the documented compat/operator surface in ADR-0002 Appendix A.",
                confidence=0.92,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-BE-WRITERS-ROOM-ROUTES",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="Writers’ Room review/decision routes expose the backend-first workflow described in the publishing-flow document.",
                confidence=0.93,
            ),
            RelationEdge(
                relation="operationalizes",
                source_id="OBS-AI-RAG",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="ai_stack/rag.py is the primary implementation anchor listed in RAG.md.",
                confidence=0.95,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-RUNTIME-AUTH-ONBOARDING",
                target_id="CTR-RUNTIME-AUTHORITY-STATE-FLOW",
                evidence="Onboarding doc condenses the runtime authority contract for navigation.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-GOC-PLAYER-GUIDE",
                target_id="CTR-GOC-VERTICAL-SLICE",
                evidence="Player guide summarizes GoC slice rules and canonical turn semantics for a lower-authority audience.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-PUBLISHING-ADMIN-GUIDE",
                target_id="CTR-WRITERS-ROOM-PUBLISHING-FLOW",
                evidence="Admin publishing guide restates the backend-first publishing path.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-AI-SYSTEM-RAG-SUMMARY",
                target_id="CTR-RAG-GOVERNANCE",
                evidence="AI system overview reuses RAG governance as a summarized system map.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="CTR-API-OPENAPI-001",
                target_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                evidence="The packaged backend OpenAPI artifact is bounded to route/schema inventory and remains subordinate to the higher-order canonical runtime contract for overlapping run lifecycle semantics.",
                confidence=0.88,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-README",
                target_id="CTR-API-OPENAPI-001",
                evidence="API README is explicitly governed as a projection-layer overview of the packaged OpenAPI artifact.",
                confidence=0.87,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-REFERENCE",
                target_id="CTR-API-OPENAPI-001",
                evidence="API reference is explicitly governed as a convenience projection of the packaged OpenAPI artifact.",
                confidence=0.84,
            ),
            RelationEdge(
                relation="depends_on",
                source_id="PRJ-API-REFERENCE",
                target_id="CTR-CANONICAL-RUNTIME-CONTRACT",
                evidence="Where the reference mentions run lifecycle payload semantics, it remains subordinate to the canonical runtime contract.",
                confidence=0.82,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-POSTMAN-GUIDE",
                target_id="CTR-API-OPENAPI-001",
                evidence="Postman guide is governed as an operational projection rooted in the packaged OpenAPI artifact.",
                confidence=0.84,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-API-EXPLORER-STRATEGY",
                target_id="CTR-API-OPENAPI-001",
                evidence="Strategy doc records the projection layer around the packaged OpenAPI artifact without becoming the primary contract itself.",
                confidence=0.83,
            ),
            RelationEdge(
                relation="derives_from",
                source_id="PRJ-POSTMAN-README",
                target_id="CTR-API-OPENAPI-001",
                evidence="Postman README classifies generated collections as convenience projections derived from the packaged OpenAPI artifact.",
                confidence=0.84,
            ),
        ]
    )

    unresolved_candidates = [
        ConflictFinding(
            id="CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT",
            conflict_type="intentional_unresolved_transition_boundary",
            summary="Backend transitional retirement remains intentionally unresolved for the backend-local trio, but the boundary is now closure-prepared: session_routes, session_store, and session_service remain retirement-open while world_engine_console_routes stays separately retained operator support.",
            sources=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
            confidence=0.84,
            requires_human_review=True,
            notes="Governed as quarantine/compat today. Honest closure still requires caller/test/operator dependency evidence, explicit reclassification or removal, and proof that retained operator support is not being mistaken for the retirement-open trio.",
            classification="runtime_transition_retirement_closure_prepared_but_still_open",
            normative_sources=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ],
            observed_or_projection_sources=[
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
            kind="intentional_unresolved_boundary",
            severity="medium",
            normative_candidates=[
                _adr0002(repo),
                "docs/technical/architecture/backend-runtime-classification.md",
                "governance/V24_BACKEND_TRANSITIONAL_RETIREMENT_LEDGER.md",
            ],
            observed_candidates=[
                "backend/app/api/v1/session_routes.py",
                "backend/app/runtime/session_store.py",
                "backend/app/services/session_service.py",
            ],
        ),
        ConflictFinding(
            id="CNF-RUNTIME-SPINE-API-PROJECTION-GOVERNANCE",
            conflict_type="intentional_projection_boundary",
            summary="API-facing docs and Postman assets are intentionally governed as lower-order projections of the bounded OpenAPI schema and higher-order canonical runtime/API contracts; partial schema depth and projection drift risk remain visible.",
            sources=[
                "docs/api/openapi.yaml",
                "docs/api/README.md",
                "docs/api/REFERENCE.md",
                "docs/api/POSTMAN_COLLECTION.md",
                "docs/dev/api/openapi-and-api-explorer-strategy.md",
                "postman/README.md",
                "postman/postmanify-manifest.json",
            ],
            confidence=0.82,
            requires_human_review=True,
            notes="Not a contradiction today; keep visible so convenience docs, generated collections, or partial schema coverage do not drift into a second competing API truth layer.",
            classification="api_projection_layer_bounded_but_not_fully_closed",
            normative_sources=[
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/api/openapi.yaml",
                "governance/V24_API_PROJECTION_GOVERNANCE_LEDGER.md",
            ],
            observed_or_projection_sources=[
                "docs/api/README.md",
                "docs/api/REFERENCE.md",
                "docs/api/POSTMAN_COLLECTION.md",
                "docs/dev/api/openapi-and-api-explorer-strategy.md",
                "postman/README.md",
                "postman/postmanify-manifest.json",
                "postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json",
            ],
            kind="projection_drift_boundary",
            severity="medium",
            normative_candidates=[
                "docs/technical/architecture/canonical_runtime_contract.md",
                "docs/technical/runtime/runtime-authority-and-state-flow.md",
                "docs/api/openapi.yaml",
                "governance/V24_API_PROJECTION_GOVERNANCE_LEDGER.md",
            ],
            observed_candidates=[
                "docs/api/README.md",
                "docs/api/REFERENCE.md",
                "docs/api/POSTMAN_COLLECTION.md",
                "docs/dev/api/openapi-and-api-explorer-strategy.md",
                "postman/README.md",
                "postman/postmanify-manifest.json",
            ],
        ),
        ConflictFinding(
            id="CNF-RUNTIME-SPINE-WRITERS-RAG-OVERLAP",
            conflict_type="intentional_overlap_boundary",
            summary="Writers’ Room workflow and RAG governance intentionally overlap only at retrieval_context_provider and context_pack_assembly support; publish_authority, canonical promotion, and runtime truth remain separate and must stay explicitly reviewed.",
            sources=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
            confidence=0.8,
            requires_human_review=True,
            notes="Not a contradiction today; keep reviewable so future retrieval write-backs, auto-publish semantics, or runtime write-through paths do not flatten authority boundaries. Re-audit must verify that retrieval output remains support/context only.",
            classification="intentional_overlap_boundary_narrowed_to_context_support",
            normative_sources=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
                "governance/V24_WRITERS_ROOM_RAG_OVERLAP_LEDGER.md",
            ],
            observed_or_projection_sources=[
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
            kind="reviewable_overlap",
            severity="medium",
            normative_candidates=[
                "docs/technical/content/writers-room-and-publishing-flow.md",
                "docs/technical/ai/RAG.md",
                "governance/V24_WRITERS_ROOM_RAG_OVERLAP_LEDGER.md",
            ],
            observed_candidates=[
                "backend/app/api/v1/writers_room_routes.py",
                "ai_stack/rag.py",
            ],
        ),
    ]
    unresolved = [
        finding
        for finding in unresolved_candidates
        if _has_current_repo_evidence(repo, finding)
    ]

    families = {
        "runtime_authority": [
            "CTR-ADR-0001-RUNTIME-AUTHORITY",
            "CTR-ADR-0002-BACKEND-SESSION-QUARANTINE",
            "CTR-RUNTIME-AUTHORITY-STATE-FLOW",
            "CTR-BACKEND-RUNTIME-CLASSIFICATION",
            "CTR-CANONICAL-RUNTIME-CONTRACT",
        ],
        "input_turn": [
            "CTR-PLAYER-INPUT-INTERPRETATION",
            "OBS-CORE-INPUT-INTERPRETER",
            "VER-CORE-INPUT-INTERPRETER-TEST",
        ],
        "goc": [
            "CTR-GOC-VERTICAL-SLICE",
            "CTR-GOC-CANONICAL-TURN",
            "CTR-GOC-GATE-SCORING",
            "VER-GOC-EXPERIENCE-SCORE-CLI-TEST",
        ],
        "scene_identity": [
            "CTR-ADR-0003-SCENE-IDENTITY",
            "OBS-AI-GOC-SCENE-IDENTITY",
            "OBS-AI-GOC-YAML-AUTHORITY",
            "VER-AI-GOC-SCENE-IDENTITY-TEST",
        ],
        "publish_rag": [
            "CTR-WRITERS-ROOM-PUBLISHING-FLOW",
            "CTR-RAG-GOVERNANCE",
            "OBS-BE-WRITERS-ROOM-ROUTES",
            "OBS-AI-RAG",
        ],
        "api_projection": [
            "CTR-API-OPENAPI-001",
            "PRJ-API-README",
            "PRJ-API-REFERENCE",
            "PRJ-API-POSTMAN-GUIDE",
            "PRJ-API-EXPLORER-STRATEGY",
            "PRJ-POSTMAN-README",
        ],
        "testing": [
            "CTR-TESTING-ORCHESTRATION",
            "VER-TEST-RUNNER-CLI",
            "VER-SMOKE-DOCUMENTED-PATHS",
        ],
    }

    return contracts, projections, relations, unresolved, families
