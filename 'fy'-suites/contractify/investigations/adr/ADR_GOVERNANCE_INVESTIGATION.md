# ADR governance investigation

- Canonical ADR home: `docs/ADR`
- ADR files discovered: 29
- Canonical ADR files already in place: 29
- Legacy ADR files still outside `docs/ADR`: 0
- Findings: 0

## What this suite is for

This investigation suite makes ADR state visible in one place: current locations, proposed canonical names, duplicate pressure, migration gaps, and relation maps into the governed runtime/MVP spine.

## ADR inventory

| Current path | Declared id | Status | Family | Proposed canonical id | Proposed canonical path | Issues |
|---|---|---|---|---|---|---|
| `docs/ADR/adr-0015-persist-turnexecutionresult-and-aidecisionlog.md` | `ADR-0015` | `accepted_(closure_decision_from_w2/w3_closure)` | `AI.RAG` | `ADR.AI.RAG.0015` | `docs/ADR/ADR.AI.RAG.0015-persist-turnexecutionresult-and-aidecisionlog-in-sessionstate.md` | none |
| `docs/ADR/adr-0016-frontend-backend-restructure.md` | `ADR-0016` | `proposed` | `AI.RAG` | `ADR.AI.RAG.0016` | `docs/ADR/ADR.AI.RAG.0016-frontend-backend-restructure-separate-backend-and-administration-tool-frontend.md` | none |
| `docs/ADR/adr-0024-decision-boundary-record-schema.md` | `ADR-0024` | `proposed` | `AI.RAG` | `ADR.AI.RAG.0024` | `docs/ADR/ADR.AI.RAG.0024-decision-boundary-record-minimum-schema-for-decision-boundary-recording.md` | none |
| `docs/ADR/adr-0025-canonical-authored-content-model.md` | `ADR-0025` | `proposed` | `AI.RAG` | `ADR.AI.RAG.0025` | `docs/ADR/ADR.AI.RAG.0025-canonical-authored-content-model.md` | none |
| `docs/ADR/adr-0002-backend-session-surface-quarantine.md` | `ADR-0002` | `accepted` | `BACKEND.SESSION` | `ADR.BACKEND.SESSION.0002` | `docs/ADR/ADR.BACKEND.SESSION.0002-backend-session-transitional-runtime-surface-quarantine-and-retirement.md` | none |
| `docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md` | `ADR-0004` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0004` | `docs/ADR/ADR.GENERAL.0004-runtime-model-output-is-proposal-only-until-validator-approval.md` | none |
| `docs/ADR/adr-0005-research-may-draft-change-but-may-not-publish.md` | `ADR-0005` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0005` | `docs/ADR/ADR.GENERAL.0005-research-may-draft-change-but-may-not-publish-change.md` | none |
| `docs/ADR/adr-0006-revision-review-uses-state-machine.md` | `ADR-0006` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0006` | `docs/ADR/ADR.GENERAL.0006-revision-review-uses-a-state-machine-not-loose-status-strings.md` | none |
| `docs/ADR/adr-0007-revision-conflicts-explicit-governance-objects.md` | `ADR-0007` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0007` | `docs/ADR/ADR.GENERAL.0007-revision-conflicts-are-explicit-governance-objects.md` | none |
| `docs/ADR/adr-0008-validation-strategy-explicit-configurable.md` | `ADR-0008` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0008` | `docs/ADR/ADR.GENERAL.0008-validation-strategy-must-be-explicit-and-configurable.md` | none |
| `docs/ADR/adr-0009-evaluation-is-a-promotion-gate.md` | `ADR-0009` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0009` | `docs/ADR/ADR.GENERAL.0009-evaluation-is-a-promotion-gate.md` | none |
| `docs/ADR/adr-0010-governance-workflows-event-driven.md` | `ADR-0010` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0010` | `docs/ADR/ADR.GENERAL.0010-governance-workflows-are-event-driven.md` | none |
| `docs/ADR/adr-0011-validation-failures-degrade-gracefully.md` | `ADR-0011` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0011` | `docs/ADR/ADR.GENERAL.0011-validation-failures-in-live-play-must-degrade-gracefully.md` | none |
| `docs/ADR/adr-0012-corrective-retry-provide-actionable-feedback.md` | `ADR-0012` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0012` | `docs/ADR/ADR.GENERAL.0012-corrective-retry-must-provide-actionable-validation-feedback.md` | none |
| `docs/ADR/adr-0013-preview-sessions-isolated-from-active-runtime.md` | `ADR-0013` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0013` | `docs/ADR/ADR.GENERAL.0013-preview-sessions-must-be-isolated-from-active-runtime.md` | none |
| `docs/ADR/adr-0014-player-affect-enum-signals.md` | `ADR-0014` | `proposed_(migrated_excerpt_from_mvp_docs)` | `GENERAL` | `ADR.GENERAL.0014` | `docs/ADR/ADR.GENERAL.0014-player-affect-uses-enum-based-signals-not-one-off-frustration-booleans.md` | none |
| `docs/ADR/adr-0017-durable-truth-migration-policy.md` | `ADR-0017` | `proposed` | `GENERAL` | `ADR.GENERAL.0017` | `docs/ADR/ADR.GENERAL.0017-durable-truth-migration-verification-and-archive-policy.md` | none |
| `docs/ADR/adr-0018-role-aware-aidecisionlog.md` | `ADR-0018` | `proposed` | `GENERAL` | `ADR.GENERAL.0018` | `docs/ADR/ADR.GENERAL.0018-role-aware-aidecisionlog-and-parsedroleawaredecision.md` | none |
| `docs/ADR/adr-0019-proposal-source-and-responder-gating.md` | `ADR-0019` | `accepted` | `GENERAL` | `ADR.GENERAL.0019` | `docs/ADR/ADR.GENERAL.0019-proposalsource-enum-and-responder-only-gating.md` | none |
| `docs/ADR/adr-0020-debug-panel-ui.md` | `ADR-0020` | `accepted` | `GENERAL` | `ADR.GENERAL.0020` | `docs/ADR/ADR.GENERAL.0020-debug-panel-ui-bounded-diagnostics-in-session-ui.md` | none |
| `docs/ADR/adr-0022-mvp-expansion-decision-rule.md` | `ADR-0022` | `proposed` | `GENERAL` | `ADR.GENERAL.0022` | `docs/ADR/ADR.GENERAL.0022-mvp-expansion-decision-rule-when-not-to-expand-the-platform.md` | none |
| `docs/ADR/adr-0023-decision-framework-for-risk-and-kill-criteria.md` | `ADR-0023` | `proposed` | `GENERAL` | `ADR.GENERAL.0023` | `docs/ADR/ADR.GENERAL.0023-decision-framework-risk-framing-and-kill-criteria.md` | none |
| `docs/ADR/adr-0026-mcp-host-and-runtime-phase-a.md` | `ADR-0026` | `proposed` | `GENERAL` | `ADR.GENERAL.0026` | `docs/ADR/ADR.GENERAL.0026-mcp-phase-a-host-runtime-defaults.md` | none |
| `docs/ADR/adr-0027-mcp-transport-connectivity-phase-a.md` | `ADR-0027` | `proposed` | `GENERAL` | `ADR.GENERAL.0027` | `docs/ADR/ADR.GENERAL.0027-mcp-transport-connectivity-phase-a-defaults.md` | none |
| `docs/ADR/adr-0028-mcp-security-baseline-phase-a.md` | `ADR-0028` | `proposed` | `GENERAL` | `ADR.GENERAL.0028` | `docs/ADR/ADR.GENERAL.0028-mcp-security-baseline-phase-a-minimal-policy.md` | none |
| `docs/ADR/adr-0029-residue-removal-policy.md` | `ADR-0029` | `proposed` | `GENERAL` | `ADR.GENERAL.0029` | `docs/ADR/ADR.GENERAL.0029-residue-removal-policy-operational-criteria-and-handling.md` | none |
| `docs/ADR/adr-0001-runtime-authority-in-world-engine.md` | `ADR-0001` | `accepted` | `RUNTIME` | `ADR.RUNTIME.0001` | `docs/ADR/ADR.RUNTIME.0001-runtime-authority-in-world-engine.md` | none |
| `docs/ADR/adr-0021-runtime-authority.md` | `ADR-0021` | `superseded_by_ADR-0001` | `RUNTIME` | `ADR.RUNTIME.0021` | `docs/ADR/ADR.RUNTIME.0021-runtime-authority-world-engine-as-authoritative-runtime-host.md` | duplicate stub — normative record is ADR-0001 |
| `docs/ADR/adr-0003-scene-identity-canonical-surface.md` | `ADR-0003` | `accepted` | `SLICE.GOC` | `ADR.SLICE.GOC.0003` | `docs/ADR/ADR.SLICE.GOC.0003-single-canonical-scene-identity-surface-across-compile-ai-guidance-and-commit.md` | none |

## Findings

| Kind | Severity | Summary | Recommended action | Sources |
|---|---|---|---|---|
| none | none | no current ADR governance findings | keep canonical placement stable | — |

## Governed runtime/MVP ADR attachment view

| ADR contract | Anchor | Implemented by | Validated by | Documented in | Precedence |
|---|---|---|---|---|---|
| `CTR-ADR-0001-RUNTIME-AUTHORITY` | `docs/ADR/adr-0001-runtime-authority-in-world-engine.md` | `world-engine/app/story_runtime/manager.py`, `world-engine/app/api/http.py` | `world-engine/tests/test_story_runtime_api.py` | `docs/technical/runtime/runtime-authority-and-state-flow.md`, `docs/dev/architecture/runtime-authority-and-session-lifecycle.md` | `runtime_authority` |
| `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE` | `docs/ADR/adr-0002-backend-session-surface-quarantine.md` | `backend/app/api/v1/session_routes.py`, `backend/app/runtime/session_store.py`, `backend/app/services/session_service.py`, `backend/app/api/v1/world_engine_console_routes.py` | `backend/tests/test_session_routes.py`, `backend/tests/test_world_engine_console_routes.py` | `docs/technical/architecture/backend-runtime-classification.md`, `docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md` | `runtime_authority` |
| `CTR-ADR-0003-SCENE-IDENTITY` | `docs/ADR/adr-0003-scene-identity-canonical-surface.md` | `ai_stack/goc_scene_identity.py`, `ai_stack/goc_yaml_authority.py` | `ai_stack/tests/test_goc_scene_identity.py` | `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/ADR/README.md` | `slice_normative` |

## Maps

- Relation map: `ADR_RELATION_MAP.mmd`
- Conflict / gap map: `ADR_CONFLICT_MAP.mmd`

## Gaps to keep visible

- manual unresolved `CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT` — Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.
