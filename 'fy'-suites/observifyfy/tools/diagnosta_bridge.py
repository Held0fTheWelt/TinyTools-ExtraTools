"""Read bounded Diagnosta status for observifyfy."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from fy_platform.ai.strategy_profiles import strategy_runtime_metadata


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_diagnosta_signal(repo_root: Path) -> dict[str, Any]:
    """Load the latest Diagnosta outputs that observifyfy can surface."""
    active_profile = strategy_runtime_metadata(repo_root)
    reports_root = repo_root / "diagnosta" / "reports"
    readiness_path = reports_root / "latest_readiness_case.json"
    blocker_path = reports_root / "latest_blocker_graph.json"
    priority_path = reports_root / "latest_blocker_priority_report.json"
    cannot_path = reports_root / "latest_cannot_honestly_claim.json"
    guarantee_gap_path = reports_root / "latest_guarantee_gap_report.md"
    deep_synthesis_path = reports_root / "latest_deep_synthesis.json"
    handoff_path = reports_root / "latest_handoff_packet.json"
    if not readiness_path.is_file():
        return {
            "present": False,
            "active_strategy_profile": active_profile,
            "readiness_case": None,
            "blocker_graph": None,
            "blocker_priority_report": None,
            "cannot_honestly_claim": None,
            "deep_synthesis": None,
            "handoff_packet": None,
            "suggested_next_wave": None,
        }
    readiness_case = _load_json(readiness_path)
    blocker_graph = _load_json(blocker_path) if blocker_path.is_file() else None
    blocker_priority_report = (
        _load_json(priority_path) if priority_path.is_file() else {"priorities": []}
    )
    cannot_honestly_claim = _load_json(cannot_path) if cannot_path.is_file() else None
    deep_synthesis = _load_json(deep_synthesis_path) if deep_synthesis_path.is_file() else None
    handoff_packet = _load_json(handoff_path) if handoff_path.is_file() else None
    priorities = list((blocker_priority_report or {}).get("priorities") or [])
    top = priorities[0] if priorities else None
    suggested_next_wave = None
    if top:
        suggested_next_wave = {
            "suite": top.get("suite", "diagnosta"),
            "priority": top.get("severity", "medium"),
            "summary": top.get("summary", ""),
            "recommended_action": (
                f"Plan the next bounded wave against {top.get('suite', 'diagnosta')} "
                f"to address blocker {top.get('blocker_id', 'unknown')}."
            ),
        }
    return {
        "present": True,
        "active_strategy_profile": active_profile,
        "readiness_case": readiness_case,
        "blocker_graph": blocker_graph,
        "blocker_priority_report": blocker_priority_report,
        "cannot_honestly_claim": cannot_honestly_claim,
        "deep_synthesis": deep_synthesis,
        "handoff_packet": handoff_packet,
        "guarantee_gap_report_path": (
            str(guarantee_gap_path.relative_to(repo_root)) if guarantee_gap_path.is_file() else ""
        ),
        "profile_depth_signal": {
            "profile_execution_lane": active_profile.get("profile_execution_lane"),
            "profile_behavior_depth": active_profile.get("profile_behavior_depth"),
            "planning_horizon": (deep_synthesis or {}).get("planning_horizon", active_profile.get("planning_horizon", 1)),
            "blocker_cluster_count": len((deep_synthesis or {}).get("blocker_clusters") or []),
            "guarantee_gap_cluster_count": len((deep_synthesis or {}).get("guarantee_gap_clusters") or []),
            "next_wave_count": len((deep_synthesis or {}).get("next_wave_plan") or []),
            "handoff_depth": (handoff_packet or {}).get("depth", active_profile.get("handoff_depth")),
        },
        "suggested_next_wave": suggested_next_wave,
    }
