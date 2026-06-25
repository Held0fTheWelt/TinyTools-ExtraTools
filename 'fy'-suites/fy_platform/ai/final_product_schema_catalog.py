"""Legacy final-product schema catalog grouped by concern."""
from __future__ import annotations

from typing import Any


def schema_for_object(name: str, fields: dict[str, Any], *, schema_version: str) -> dict[str, Any]:
    """Build a single JSON schema object payload."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "schema_version": schema_version,
        "properties": fields,
        "additionalProperties": True,
    }


def _command_and_run_schemas() -> dict[str, dict[str, Any]]:
    return {
        "command_envelope.schema.json": schema_for_object(
            "CommandEnvelope",
            {
                "ok": {"type": "boolean"},
                "suite": {"type": "string"},
                "command": {"type": "string"},
                "payload": {"type": "object"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "recovery_hints": {"type": "array", "items": {"type": "string"}},
                "error_code": {"type": ["string", "null"]},
            },
            schema_version="fy.command-envelope.schema.v1",
        ),
        "suite_run_record.schema.json": schema_for_object(
            "SuiteRunRecord",
            {
                "run_id": {"type": "string"},
                "suite": {"type": "string"},
                "mode": {"type": "string"},
                "started_at": {"type": "string"},
                "ended_at": {"type": ["string", "null"]},
                "workspace_root": {"type": "string"},
                "target_repo_root": {"type": ["string", "null"]},
                "target_repo_id": {"type": ["string", "null"]},
                "status": {"type": "string"},
                "strategy_profile": {"type": "string"},
                "run_metadata": {"type": "object"},
            },
            schema_version="fy.suite-run.schema.v1",
        ),
        "evidence_record.schema.json": schema_for_object(
            "EvidenceRecord",
            {
                "evidence_id": {"type": "string"},
                "suite": {"type": "string"},
                "run_id": {"type": "string"},
                "kind": {"type": "string"},
                "source_uri": {"type": "string"},
                "ownership_zone": {"type": "string"},
                "content_hash": {"type": "string"},
                "mime_type": {"type": "string"},
                "deterministic": {"type": "boolean"},
                "review_state": {"type": "string"},
                "created_at": {"type": "string"},
            },
            schema_version="fy.evidence-record.schema.v1",
        ),
        "artifact_record.schema.json": schema_for_object(
            "ArtifactRecord",
            {
                "artifact_id": {"type": "string"},
                "suite": {"type": "string"},
                "run_id": {"type": "string"},
                "format": {"type": "string"},
                "role": {"type": "string"},
                "path": {"type": "string"},
                "created_at": {"type": "string"},
            },
            schema_version="fy.artifact-record.schema.v1",
        ),
    }


def _context_and_routing_schemas() -> dict[str, dict[str, Any]]:
    return {
        "context_pack.schema.json": schema_for_object(
            "ContextPack",
            {
                "pack_id": {"type": "string"},
                "query": {"type": "string"},
                "suite_scope": {"type": "array", "items": {"type": "string"}},
                "audience": {"type": "string"},
                "hits": {"type": "array", "items": {"type": "object"}},
                "summary": {"type": "string"},
                "artifact_paths": {"type": "array", "items": {"type": "string"}},
                "related_suites": {"type": "array", "items": {"type": "string"}},
                "evidence_confidence": {"type": "string"},
                "priorities": {"type": "array", "items": {"type": "string"}},
                "next_steps": {"type": "array", "items": {"type": "string"}},
                "uncertainty": {"type": "array", "items": {"type": "string"}},
            },
            schema_version="fy.context-pack.schema.v1",
        ),
        "model_route_decision.schema.json": schema_for_object(
            "ModelRouteDecision",
            {
                "task_type": {"type": "string"},
                "selected_tier": {"type": "string"},
                "selected_model": {"type": "string"},
                "reason": {"type": "string"},
                "budget_class": {"type": "string"},
                "fallback_chain": {"type": "array", "items": {"type": "string"}},
                "reproducibility_mode": {"type": "string"},
                "safety_mode": {"type": "string"},
                "estimated_cost_class": {"type": "string"},
            },
            schema_version="fy.model-route-decision.schema.v1",
        ),
        "compare_runs_delta.schema.json": schema_for_object(
            "CompareRunsDelta",
            {
                "left_run_id": {"type": "string"},
                "right_run_id": {"type": "string"},
                "left_status": {"type": "string"},
                "right_status": {"type": "string"},
                "artifact_delta": {"type": "integer"},
                "added_roles": {"type": "array", "items": {"type": "string"}},
                "removed_roles": {"type": "array", "items": {"type": "string"}},
                "left_artifact_count": {"type": "integer"},
                "right_artifact_count": {"type": "integer"},
                "left_evidence_count": {"type": "integer"},
                "right_evidence_count": {"type": "integer"},
                "left_review_state_counts": {"type": "object"},
                "right_review_state_counts": {"type": "object"},
                "left_journal_event_count": {"type": "integer"},
                "right_journal_event_count": {"type": "integer"},
                "left_duration_seconds": {"type": ["number", "null"]},
                "right_duration_seconds": {"type": ["number", "null"]},
                "mode_changed": {"type": "boolean"},
                "target_repo_changed": {"type": "boolean"},
                "target_repo_id_changed": {"type": "boolean"},
                "left_strategy_profile": {"type": "string"},
                "right_strategy_profile": {"type": "string"},
                "strategy_profile_changed": {"type": "boolean"},
                "added_formats": {"type": "array", "items": {"type": "string"}},
                "removed_formats": {"type": "array", "items": {"type": "string"}},
            },
            schema_version="fy.compare-runs-delta.schema.v1",
        ),
    }


def _readiness_case_schemas() -> dict[str, dict[str, Any]]:
    return {
        "readiness_case.schema.json": schema_for_object(
            "ReadinessCase",
            {
                "readiness_case_id": {"type": "string"},
                "target_id": {"type": "string"},
                "target_kind": {"type": "string"},
                "active_profile": {"type": "string"},
                "readiness_status": {"type": "string"},
                "summary": {"type": "string"},
                "blocker_ids": {"type": "array", "items": {"type": "string"}},
                "obligation_ids": {"type": "array", "items": {"type": "string"}},
                "sufficiency_verdict_id": {"type": "string"},
                "cannot_honestly_claim_id": {"type": "string"},
                "residue_ids": {"type": "array", "items": {"type": "string"}},
                "evidence_sources": {"type": "array", "items": {"type": "string"}},
            },
            schema_version="fy.readiness-case.schema.v1",
        ),
        "blocker_graph.schema.json": schema_for_object(
            "BlockerGraph",
            {
                "blocker_graph_id": {"type": "string"},
                "target_id": {"type": "string"},
                "nodes": {"type": "array", "items": {"type": "object"}},
                "edges": {"type": "array", "items": {"type": "object"}},
                "summary": {"type": "string"},
            },
            schema_version="fy.blocker-graph.schema.v1",
        ),
        "blocker_priority_report.schema.json": schema_for_object(
            "BlockerPriorityReport",
            {
                "report_id": {"type": "string"},
                "target_id": {"type": "string"},
                "blocker_count": {"type": "integer"},
                "priorities": {"type": "array", "items": {"type": "object"}},
                "summary": {"type": "string"},
            },
            schema_version="fy.blocker-priority-report.schema.v1",
        ),
        "obligation_matrix.schema.json": schema_for_object(
            "ObligationMatrix",
            {
                "obligation_matrix_id": {"type": "string"},
                "target_id": {"type": "string"},
                "rows": {"type": "array", "items": {"type": "object"}},
                "summary": {"type": "string"},
            },
            schema_version="fy.obligation-matrix.schema.v1",
        ),
    }


def _closure_and_strategy_schemas() -> dict[str, dict[str, Any]]:
    return {
        "sufficiency_verdict.schema.json": schema_for_object(
            "SufficiencyVerdict",
            {
                "sufficiency_verdict_id": {"type": "string"},
                "target_id": {"type": "string"},
                "verdict": {"type": "string"},
                "reason": {"type": "string"},
                "supporting_artifact_paths": {"type": "array", "items": {"type": "string"}},
            },
            schema_version="fy.sufficiency-verdict.schema.v1",
        ),
        "cannot_honestly_claim.schema.json": schema_for_object(
            "CannotHonestlyClaim",
            {
                "cannot_honestly_claim_id": {"type": "string"},
                "target_id": {"type": "string"},
                "blocked_claims": {"type": "array", "items": {"type": "string"}},
                "reasons": {"type": "array", "items": {"type": "string"}},
            },
            schema_version="fy.cannot-honestly-claim.schema.v1",
        ),
        "closure_pack.schema.json": schema_for_object(
            "ClosurePack",
            {
                "closure_pack_id": {"type": "string"},
                "target_id": {"type": "string"},
                "status": {"type": "string"},
                "obligation_ids": {"type": "array", "items": {"type": "string"}},
                "residue_ids": {"type": "array", "items": {"type": "string"}},
                "review_required": {"type": "boolean"},
                "summary": {"type": "string"},
            },
            schema_version="fy.closure-pack.schema.v1",
        ),
        "residue_ledger.schema.json": schema_for_object(
            "ResidueLedger",
            {
                "residue_ledger_id": {"type": "string"},
                "target_id": {"type": "string"},
                "items": {"type": "array", "items": {"type": "object"}},
                "summary": {"type": "string"},
            },
            schema_version="fy.residue-ledger.schema.v1",
        ),
        "active_strategy_profile.schema.json": schema_for_object(
            "ActiveStrategyProfile",
            {
                "active_profile": {"type": "string"},
                "profile_label": {"type": "string"},
                "default_progression_order": {"type": "array", "items": {"type": "string"}},
                "progression_mode": {"type": "string"},
                "allow_profile_switching": {"type": "boolean"},
                "menu_enabled": {"type": "boolean"},
                "trigger_enabled": {"type": "boolean"},
                "command_enabled": {"type": "boolean"},
                "markdown_override_allowed": {"type": "boolean"},
                "require_review_by_default": {"type": "boolean"},
                "auto_apply_level": {"type": "string"},
                "diagnosta_enabled": {"type": "boolean"},
                "diagnosta_scope": {"type": "string"},
                "coda_enabled": {"type": "boolean"},
                "coda_scope": {"type": "string"},
                "emit_profile_to_run_journal": {"type": "boolean"},
                "emit_profile_to_observifyfy": {"type": "boolean"},
                "emit_profile_to_compare_runs": {"type": "boolean"},
                "emit_profile_to_status_pages": {"type": "boolean"},
                "compare_profile_effects": {"type": "string"},
                "allow_candidate_e_features": {"type": "boolean"},
                "candidate_e_requires_explicit_opt_in": {"type": "boolean"},
                "source_path": {"type": "string"},
            },
            schema_version="fy.active-strategy-profile.schema.v1",
        ),
    }


def legacy_schema_payloads() -> dict[str, dict[str, Any]]:
    return {
        **_command_and_run_schemas(),
        **_context_and_routing_schemas(),
        **_readiness_case_schemas(),
        **_closure_and_strategy_schemas(),
    }


__all__ = ["legacy_schema_payloads", "schema_for_object"]
