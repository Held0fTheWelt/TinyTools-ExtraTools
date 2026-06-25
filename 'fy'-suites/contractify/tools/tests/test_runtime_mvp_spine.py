from __future__ import annotations

from pathlib import Path

from contractify.tools.audit_pipeline import run_audit
from contractify.tools.conflicts import detect_all_conflicts
from contractify.tools.discovery import discover_contracts_and_projections
from contractify.tools.relations import extend_relations


def _write(path: Path, text: str = "fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _runtime_spine_repo(root: Path) -> Path:
    _write(root / "pyproject.toml", '[project]\nname = "world-of-shadows-hub"\n')
    _write(
        root / "docs" / "api" / "openapi.yaml",
        "openapi: 3.0.0\ninfo:\n  title: Runtime spine fixture\n  version: '0.0.1'\npaths: {}\n",
    )
    _write(
        root / "docs" / "ADR" / "adr-0001-runtime-authority-in-world-engine.md",
        "# ADR-0001\n\nStatus: Accepted\n\nRuntime authority belongs to world-engine.\n",
    )
    _write(
        root / "docs" / "ADR" / "adr-0002-backend-session-surface-quarantine.md",
        "# ADR-0002\n\nStatus: Accepted\n\nRuntime authority and session surface quarantine.\n",
    )
    _write(
        root / "docs" / "ADR" / "adr-0003-scene-identity-canonical-surface.md",
        "# ADR-0003\n\nStatus: Accepted\n\nScene identity is canonical for GoC.\n",
    )

    for rel in [
        "docs/technical/runtime/runtime-authority-and-state-flow.md",
        "docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md",
        "docs/technical/runtime/player_input_interpretation_contract.md",
        "docs/technical/architecture/backend-runtime-classification.md",
        "docs/technical/architecture/canonical_runtime_contract.md",
        "docs/technical/architecture/service-boundaries.md",
        "docs/technical/content/writers-room-and-publishing-flow.md",
        "docs/technical/ai/RAG.md",
        "docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md",
        "docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md",
        "docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md",
        "docs/dev/onboarding.md",
        "docs/user/god-of-carnage-player-guide.md",
        "docs/admin/publishing-and-module-activation.md",
        "docs/ai/ai_system_in_world_of_shadows.md",
        "docs/audit/gate_G9_experience_acceptance_baseline.md",
        "docs/audit/evidence_artifact_mapping_table.md",
        "docs/audit/repo_evidence_index.md",
        "docs/goc_evidence_templates/README.md",
        "tests/TESTING.md",
        "postman/postmanify-manifest.json",
    ]:
        _write(root / rel)

    for rel in [
        "world-engine/app/story_runtime/manager.py",
        "world-engine/app/api/http.py",
        "world-engine/tests/test_story_runtime_api.py",
        "backend/app/api/v1/session_routes.py",
        "backend/app/runtime/session_store.py",
        "backend/app/services/session_service.py",
        "backend/app/api/v1/world_engine_console_routes.py",
        "backend/app/api/v1/writers_room_routes.py",
        "backend/app/services/game_service.py",
        "backend/tests/test_session_routes.py",
        "backend/tests/test_session_api_contracts.py",
        "backend/tests/services/test_session_service.py",
        "backend/tests/writers_room/test_writers_room_routes.py",
        "tests/smoke/test_backend_transitional_retirement_surface_contracts.py",
        "tests/smoke/test_repository_documented_paths_resolve.py",
        "tests/experience_scoring_cli/test_experience_score_matrix_cli.py",
        "story_runtime_core/input_interpreter.py",
        "story_runtime_core/tests/test_input_interpreter.py",
        "ai_stack/goc_scene_identity.py",
        "ai_stack/goc_yaml_authority.py",
        "ai_stack/rag.py",
        "ai_stack/tests/test_goc_scene_identity.py",
        "ai_stack/tests/test_rag.py",
    ]:
        _write(root / rel)
    return root


def test_runtime_mvp_spine_promotes_mandatory_docs(tmp_path: Path) -> None:
    root = _runtime_spine_repo(tmp_path)
    contracts, _p, _r = discover_contracts_and_projections(root, max_contracts=60)
    ids = {c.id for c in contracts}
    assert {
        "CTR-RUNTIME-AUTHORITY-STATE-FLOW",
        "CTR-PLAYER-INPUT-INTERPRETATION",
        "CTR-GOC-VERTICAL-SLICE",
        "CTR-GOC-CANONICAL-TURN",
        "CTR-GOC-GATE-SCORING",
        "CTR-BACKEND-RUNTIME-CLASSIFICATION",
        "CTR-CANONICAL-RUNTIME-CONTRACT",
        "CTR-WRITERS-ROOM-PUBLISHING-FLOW",
        "CTR-RAG-GOVERNANCE",
    }.issubset(ids)


def test_runtime_mvp_relations_cover_required_edges(tmp_path: Path) -> None:
    root = _runtime_spine_repo(tmp_path)
    contracts, projections, base = discover_contracts_and_projections(root, max_contracts=60)
    conflicts = detect_all_conflicts(root, projections, contract_ids=frozenset(c.id for c in contracts), contracts=contracts)
    relations = extend_relations(root, contracts, projections, base, conflicts=conflicts)
    kinds = {(r.relation, r.source_id, r.target_id) for r in relations}
    expected = {
        ("refines", "CTR-RUNTIME-AUTHORITY-STATE-FLOW", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("refines", "CTR-BACKEND-RUNTIME-CLASSIFICATION", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("operationalizes", "CTR-BACKEND-RUNTIME-CLASSIFICATION", "CTR-ADR-0002-BACKEND-SESSION-QUARANTINE"),
        ("depends_on", "CTR-CANONICAL-RUNTIME-CONTRACT", "CTR-ADR-0001-RUNTIME-AUTHORITY"),
        ("implemented_by", "CTR-CANONICAL-RUNTIME-CONTRACT", "OBS-WE-HTTP-API"),
        ("implemented_by", "CTR-CANONICAL-RUNTIME-CONTRACT", "OBS-BE-GAME-SERVICE"),
        ("implemented_by", "CTR-PLAYER-INPUT-INTERPRETATION", "OBS-CORE-INPUT-INTERPRETER"),
        ("validated_by", "CTR-PLAYER-INPUT-INTERPRETATION", "VER-CORE-INPUT-INTERPRETER-TEST"),
        ("derives_from", "CTR-GOC-CANONICAL-TURN", "CTR-GOC-VERTICAL-SLICE"),
        ("depends_on", "CTR-GOC-GATE-SCORING", "CTR-GOC-CANONICAL-TURN"),
        ("depends_on", "CTR-GOC-GATE-SCORING", "CTR-GOC-VERTICAL-SLICE"),
        ("implemented_by", "CTR-ADR-0003-SCENE-IDENTITY", "OBS-AI-GOC-SCENE-IDENTITY"),
        ("validated_by", "CTR-ADR-0003-SCENE-IDENTITY", "VER-AI-GOC-SCENE-IDENTITY-TEST"),
        ("overlaps_with", "CTR-WRITERS-ROOM-PUBLISHING-FLOW", "CTR-RAG-GOVERNANCE"),
        ("implemented_by", "CTR-RAG-GOVERNANCE", "OBS-AI-RAG"),
    }
    missing = expected - kinds
    assert not missing, f"missing curated runtime/MVP relations: {sorted(missing)}"


def test_runtime_mvp_audit_includes_precedence_and_manual_unresolved(tmp_path: Path) -> None:
    root = _runtime_spine_repo(tmp_path)
    payload = run_audit(root, max_contracts=60)
    tiers = {row["tier"] for row in payload["precedence_rules"]}
    assert {
        "runtime_authority",
        "slice_normative",
        "implementation_evidence",
        "verification_evidence",
        "projection_low",
    } == tiers
    assert payload["manual_unresolved_areas"]
    assert payload["runtime_mvp_families"]["runtime_authority"]


def test_governed_runtime_adr_overlap_no_longer_raises_normative_vocabulary_overlap(tmp_path: Path) -> None:
    root = _runtime_spine_repo(tmp_path)
    contracts, projections, _r = discover_contracts_and_projections(root, max_contracts=60)
    conflicts = detect_all_conflicts(root, projections, contract_ids=frozenset(c.id for c in contracts), contracts=contracts)
    governed = {
        "adr-0001-runtime-authority-in-world-engine.md",
        "adr-0002-backend-session-surface-quarantine.md",
    }
    for conflict in conflicts:
        if conflict.classification != "normative_vocabulary_overlap":
            continue
        assert not set(conflict.sources).issubset(governed)
