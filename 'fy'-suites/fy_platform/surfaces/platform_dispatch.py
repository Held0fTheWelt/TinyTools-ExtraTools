from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from fy_platform.core.project_resolver import resolve_project_root
from fy_platform.ir.catalog import IRCatalog
from fy_platform.runtime.lane_runtime import LaneRuntime
from fy_platform.runtime.mode_registry import get_mode_spec
from fy_platform.surfaces.platform_dispatch_payloads import govern_payload, run_adapter, special_generate_payload
from fy_platform.surfaces.platform_dispatch_records import record_alias, record_bundle_assets, record_decision, record_failure_finding, record_review, record_snapshot
from metrify.tools.ledger import read_events


def resolve_workspace(project_root: str) -> Path:
    return Path(project_root).expanduser().resolve() if project_root else resolve_project_root(start=Path(".").resolve())


def _dispatch_payload(public_command: str, mode_name: str, workspace: Path, spec, args) -> tuple[dict, str]:
    if public_command == "govern":
        return govern_payload(workspace, mode_name), "fy-platform"
    if public_command == "metrics" and mode_name == "governor_status":
        return _governor_status_payload(workspace), "fy-platform"
    special = special_generate_payload(workspace, mode_name) if public_command == "generate" else None
    if special is not None:
        return special
    return run_adapter(spec, workspace, args)


def platform_mode_payload(public_command: str, mode_name: str, args) -> dict:
    workspace = resolve_workspace(getattr(args, "project_root", ""))
    spec = get_mode_spec(public_command, mode_name)
    ir_catalog = IRCatalog(workspace)
    runtime = LaneRuntime(ir_catalog)
    plan = spec.to_execution_plan()
    platform_run_id = ir_catalog.new_id("platformrun")
    lane_records = runtime.begin(run_id=platform_run_id, public_command=public_command, mode_name=mode_name, plan=plan)
    lane_ids = [item.lane_execution_id for item in lane_records]
    snapshot_id = record_snapshot(ir_catalog, Path(args.target_repo).resolve() if getattr(args, "target_repo", "") else None)
    suite_name = spec.suite or "fy-platform"
    try:
        payload, suite_name = _dispatch_payload(public_command, mode_name, workspace, spec, args)
        alias_id = record_alias(ir_catalog, suite_name, public_command, mode_name)
        decision_id = record_decision(
            ir_catalog,
            reason=f"platform dispatch via compatibility surface to {suite_name}",
            lane="likely_but_review" if spec.review_required else "safe_to_apply",
            recommended_action="Keep the platform shell as the primary public entry point while legacy suite commands remain compatibility surfaces.",
        )
        review_task_id = record_review(ir_catalog, mode_name, decision_id) if spec.review_required else ""
        asset_ids = record_bundle_assets(ir_catalog, snapshot_id, payload, suite_name)
        if payload.get("ok") is False:
            finding_id = record_failure_finding(ir_catalog, suite_name, mode_name, payload, asset_ids)
            for lane_id in lane_ids:
                runtime.mark_failed(lane_id, payload.get("reason") or payload.get("error") or "command_failed")
        else:
            finding_id = ""
            refs = [item for item in [snapshot_id, alias_id, decision_id, review_task_id] if item] + asset_ids
            for lane_id in lane_ids:
                runtime.mark_completed(lane_id, output_refs=refs)
        payload.update(
            {
                "active_strategy_profile": strategy_runtime_metadata(workspace),
                "public_command": public_command,
                "mode_name": mode_name,
                "lens": spec.lens,
                "platform_run_id": platform_run_id,
                "platform_plan": [step.lane_name for step in plan.steps],
                "lane_execution_ids": lane_ids,
                "compatibility_suite": suite_name,
                "ir_refs": {
                    "snapshot_id": snapshot_id,
                    "surface_alias_id": alias_id,
                    "decision_id": decision_id,
                    "review_task_id": review_task_id,
                    "finding_id": finding_id,
                    "asset_ids": asset_ids,
                },
            }
        )
        return payload
    except Exception as exc:
        for lane_id in lane_ids:
            runtime.mark_failed(lane_id, str(exc))
        return {"ok": False, "reason": "platform_mode_exception", "error": str(exc), "public_command": public_command, "mode_name": mode_name, "platform_run_id": platform_run_id, "lane_execution_ids": lane_ids}


def _governor_status_payload(workspace: Path) -> dict:
    events = read_events(workspace / "metrify" / "state" / "ledger.jsonl")
    denied = [item for item in events if item.get("guard_allowed") is False]
    allowed = [item for item in events if item.get("guard_allowed") is True]
    return {
        "ok": True,
        "workspace_root": str(workspace),
        "ledger_path": "metrify/state/ledger.jsonl",
        "event_count": len(events),
        "governor_allowed_count": len(allowed),
        "governor_denied_count": len(denied),
        "deny_reasons": sorted({str(item.get("guard_reason", "")) for item in denied if item.get("guard_reason")}),
    }


def _emit_payload(command: str, mode_name: str, args) -> int:
    from fy_platform.surfaces.platform_dispatch_emit import emit_payload

    return emit_payload(command, mode_name, args)


def cmd_analyze(args) -> int:
    return _emit_payload("analyze", args.mode, args)


def cmd_inspect_mode(args) -> int:
    return _emit_payload("inspect", args.mode, args)


def cmd_explain_mode(args) -> int:
    return _emit_payload("explain", args.mode, args)


def cmd_generate(args) -> int:
    return _emit_payload("generate", args.mode, args)


def cmd_govern(args) -> int:
    payload = platform_mode_payload("govern", args.mode, args)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("ok") else 3


def cmd_import_mode(args) -> int:
    return _emit_payload("import", args.mode, args)


def cmd_metrics_mode(args) -> int:
    return _emit_payload("metrics", args.mode, args)
