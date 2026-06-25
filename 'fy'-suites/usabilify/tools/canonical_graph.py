from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now
from fy_platform.evolution.graph_store import stable_relation_id, stable_unit_id
from fy_platform.evolution.suite_graph_emit import persist_simple_bundle


def _unit(unit_id: str, title: str, entity_type: str, source_paths: list[str], summary: str, now: str) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "title": title,
        "entity_type": entity_type,
        "owner_suite": "usabilify",
        "source_paths": source_paths,
        "summary": summary,
        "why_it_exists": "Usabilify records bounded user-facing surfaces for usability review.",
        "contracts": [],
        "dependencies": [],
        "consumers": ["developer", "designer", "operator"],
        "commands": ["analyze --mode usability"],
        "inputs": ["target_repo_root"],
        "outputs": ["usability-audit"],
        "failure_modes": [],
        "evidence_refs": [f"source:{path}" for path in source_paths],
        "roles": ["developer", "designer"],
        "layer_status": {"technical": "observed", "ai": "available-for-projection"},
        "maturity": "evidence-fill",
        "last_verified": now,
        "stability": "observed",
        "tags": ["usability", entity_type],
    }


def persist_usabilify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    workflow_id = stable_unit_id("usabilify", "workflow", "usability-audit")
    units = [
        _unit(
            workflow_id,
            "Usability audit",
            "workflow",
            ["usabilify/adapter/service.py"],
            "Scans user-facing templates, static assets, docs, and application entrypoints.",
            now,
        )
    ]
    relations: list[dict[str, Any]] = []
    for item in payload.get("surfaces", [])[:24]:
        uid = stable_unit_id("usabilify", "runtime-surface", item["path"])
        units.append(_unit(uid, item["path"], "runtime-surface", [item["path"]], item["summary"], now))
        relations.append(
            {
                "relation_id": stable_relation_id("usabilify", workflow_id, "observes", uid),
                "from_id": workflow_id,
                "to_id": uid,
                "relation_type": "observes",
                "owner_suite": "usabilify",
                "evidence_refs": [f"source:{item['path']}"],
                "confidence": "medium",
                "created_at": now,
                "last_verified": now,
            }
        )
    artifacts = [("usability_audit.json", "usability-audit", payload, [workflow_id], "deterministic-scan")]
    return persist_simple_bundle(
        workspace=workspace,
        suite="usabilify",
        repo_root=repo_root,
        run_id=run_id,
        command="analyze",
        mode="usability",
        lane="generate",
        units=units,
        relations=relations,
        extra_artifacts=artifacts,
        validation_summary={
            "unit_count": len(units),
            "relation_count": len(relations),
            "artifact_count": len(artifacts) + 3,
            "surface_count": len(payload.get("surfaces", [])),
        },
        residual_notes=["Usabilify reports observed usability surfaces; it does not certify UX quality alone."],
    )

