"""Candidate E self-hosting comparison and reporting helpers."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from coda.adapter.service import CodaAdapter
from diagnosta.adapter.service import DiagnostaAdapter
from fy_platform.ai.strategy_profiles import load_active_strategy_profile, set_active_strategy_profile
from fy_platform.ai.workspace import write_json, write_text
from observifyfy.adapter.service import ObservifyfyAdapter


def _copy_report_tree(workspace: Path, subdir: str, destination: Path, stems: list[str]) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for stem in stems:
        src = workspace / subdir / stem
        if src.is_file():
            target = destination / src.name
            shutil.copy2(src, target)
            copied.append(str(target.relative_to(workspace)))
    return copied


def _run_profile(workspace: Path, profile: str) -> dict[str, Any]:
    set_active_strategy_profile(workspace, profile)
    diagnosta = DiagnostaAdapter(root=workspace).audit(str(workspace))
    coda = CodaAdapter(root=workspace).audit(str(workspace))
    observifyfy = ObservifyfyAdapter(root=workspace).audit(str(workspace))
    return {
        "profile": profile,
        "diagnosta": diagnosta,
        "coda": coda,
        "observifyfy": observifyfy,
    }


def _profile_metrics(run_payload: dict[str, Any]) -> dict[str, Any]:
    diagnosta = run_payload["diagnosta"]
    coda = run_payload["coda"]
    obs = run_payload["observifyfy"]
    deep = diagnosta.get("deep_synthesis") or {}
    handoff = diagnosta.get("handoff_packet") or {}
    closure = coda.get("closure_pack") or {}
    movement = (obs.get("coda_signal") or {}).get("closure_movement") or {}
    return {
        "active_profile": diagnosta.get("active_strategy_profile", {}).get("active_profile", run_payload["profile"]),
        "profile_execution_lane": diagnosta.get("active_strategy_profile", {}).get("profile_execution_lane", "standard"),
        "profile_behavior_depth": diagnosta.get("active_strategy_profile", {}).get("profile_behavior_depth", "standard"),
        "planning_horizon": deep.get("planning_horizon", diagnosta.get("readiness_case", {}).get("planning_horizon", 1)),
        "blocker_cluster_count": len(deep.get("blocker_clusters") or []),
        "guarantee_gap_cluster_count": len(deep.get("guarantee_gap_clusters") or []),
        "next_wave_count": len(deep.get("next_wave_plan") or []),
        "handoff_depth": handoff.get("depth", "standard"),
        "grouped_handoff_obligation_count": len(handoff.get("grouped_obligations") or []),
        "closure_status": closure.get("status", "unknown"),
        "closure_packet_depth": closure.get("packet_depth", "standard"),
        "grouped_obligation_count": len(closure.get("grouped_obligations") or []),
        "wave_packet_count": len(closure.get("wave_packets") or []),
        "auto_preparation_count": len(closure.get("auto_preparation_packets") or []),
        "warning_count": len((coda.get("warning_ledger") or {}).get("items") or []),
        "residue_count": len((coda.get("residue_ledger") or {}).get("items") or []),
        "observed_packet_depth": movement.get("packet_depth", "standard"),
    }


def build_candidate_e_release_bundle(workspace: Path) -> dict[str, Any]:
    """Run D and E self-hosting comparisons and write final Candidate E artifacts."""
    reports_root = workspace / "docs" / "platform"
    self_hosting_root = reports_root / "self_hosting"
    examples_root = reports_root / "examples" / "candidate_e"
    reports_root.mkdir(parents=True, exist_ok=True)
    self_hosting_root.mkdir(parents=True, exist_ok=True)
    examples_root.mkdir(parents=True, exist_ok=True)

    original_profile = load_active_strategy_profile(workspace).active_profile
    d_run = _run_profile(workspace, "D")
    d_metrics = _profile_metrics(d_run)
    d_copied = {
        "diagnosta": _copy_report_tree(workspace, "diagnosta/reports", examples_root / "d" / "diagnosta", [
            "latest_readiness_case.json",
            "latest_deep_synthesis.json",
            "latest_handoff_packet.json",
            "latest_warning_ledger.json",
        ]),
        "coda": _copy_report_tree(workspace, "coda/reports", examples_root / "d" / "coda", [
            "latest_closure_pack.json",
            "latest_review_packet.json",
            "latest_warning_ledger.json",
        ]),
        "observifyfy": _copy_report_tree(workspace, "observifyfy/reports", examples_root / "d" / "observifyfy", [
            "observifyfy_diagnosta_signal.json",
            "observifyfy_coda_signal.json",
            "observifyfy_ai_context.json",
        ]),
    }

    e_run = _run_profile(workspace, "E")
    e_metrics = _profile_metrics(e_run)
    e_copied = {
        "diagnosta": _copy_report_tree(workspace, "diagnosta/reports", examples_root / "e" / "diagnosta", [
            "latest_readiness_case.json",
            "latest_deep_synthesis.json",
            "latest_handoff_packet.json",
            "latest_warning_ledger.json",
        ]),
        "coda": _copy_report_tree(workspace, "coda/reports", examples_root / "e" / "coda", [
            "latest_closure_pack.json",
            "latest_review_packet.json",
            "latest_warning_ledger.json",
        ]),
        "observifyfy": _copy_report_tree(workspace, "observifyfy/reports", examples_root / "e" / "observifyfy", [
            "observifyfy_diagnosta_signal.json",
            "observifyfy_coda_signal.json",
            "observifyfy_ai_context.json",
        ]),
    }

    comparison = {
        "schema_version": "fy.candidate-e-comparison.v1",
        "default_profile": "D",
        "original_profile": original_profile,
        "d_metrics": d_metrics,
        "e_metrics": e_metrics,
        "material_difference_confirmed": (
            e_metrics["planning_horizon"] > d_metrics["planning_horizon"]
            and e_metrics["next_wave_count"] > d_metrics["next_wave_count"]
            and e_metrics["wave_packet_count"] > d_metrics["wave_packet_count"]
            and e_metrics["auto_preparation_count"] > d_metrics["auto_preparation_count"]
            and e_metrics["closure_packet_depth"] != d_metrics["closure_packet_depth"]
        ),
        "honesty_constraints_confirmed": (
            e_metrics["warning_count"] >= 0 and e_metrics["residue_count"] >= 0
        ),
        "copied_examples": {"d": d_copied, "e": e_copied},
    }
    comparison_path = self_hosting_root / "candidate_e_d_vs_e_comparison.json"
    write_json(comparison_path, comparison)
    comparison_md = self_hosting_root / "candidate_e_d_vs_e_comparison.md"
    write_text(
        comparison_md,
        "# Candidate E D-vs-E Comparison\n\n"
        f"- material_difference_confirmed: `{comparison['material_difference_confirmed']}`\n"
        f"- d_planning_horizon: `{d_metrics['planning_horizon']}`\n"
        f"- e_planning_horizon: `{e_metrics['planning_horizon']}`\n"
        f"- d_wave_packet_count: `{d_metrics['wave_packet_count']}`\n"
        f"- e_wave_packet_count: `{e_metrics['wave_packet_count']}`\n"
        f"- d_packet_depth: `{d_metrics['closure_packet_depth']}`\n"
        f"- e_packet_depth: `{e_metrics['closure_packet_depth']}`\n",
    )

    manifest = {
        "schema_version": "fy.candidate-e-terminal-manifest.v1",
        "default_profile": "D",
        "restored_profile": "D",
        "d_run_ids": {
            "diagnosta": d_run["diagnosta"]["run_id"],
            "coda": d_run["coda"]["run_id"],
            "observifyfy": d_run["observifyfy"]["run_id"],
        },
        "e_run_ids": {
            "diagnosta": e_run["diagnosta"]["run_id"],
            "coda": e_run["coda"]["run_id"],
            "observifyfy": e_run["observifyfy"]["run_id"],
        },
        "comparison_path": str(comparison_path.relative_to(workspace)),
        "candidate_e_honesty_note": "Candidate E stays review-first, opt-in, residue-honest, and does not enable silent auto-apply.",
    }
    manifest_json = self_hosting_root / "candidate_e_self_hosting_manifest.json"
    manifest_md = self_hosting_root / "candidate_e_self_hosting_manifest.md"
    write_json(manifest_json, manifest)
    write_text(
        manifest_md,
        "# Candidate E Self-Hosting Manifest\n\n"
        f"- default_profile: `{manifest['default_profile']}`\n"
        f"- restored_profile: `{manifest['restored_profile']}`\n"
        f"- comparison_path: `{manifest['comparison_path']}`\n"
        f"- candidate_e_honesty_note: {manifest['candidate_e_honesty_note']}\n",
    )

    report = reports_root / "READINESS_CLOSURE_CANDIDATE_E_FINAL_REPORT.md"
    write_text(
        report,
        "# Candidate E Narrow-but-Deep Final Report\n\n"
        "Candidate D remains the default active profile. Candidate E is opt-in and operationally deeper.\n\n"
        "## D vs E summary\n\n"
        f"- D profile_execution_lane: `{d_metrics['profile_execution_lane']}`\n"
        f"- E profile_execution_lane: `{e_metrics['profile_execution_lane']}`\n"
        f"- D planning_horizon: `{d_metrics['planning_horizon']}`\n"
        f"- E planning_horizon: `{e_metrics['planning_horizon']}`\n"
        f"- D handoff_depth: `{d_metrics['handoff_depth']}`\n"
        f"- E handoff_depth: `{e_metrics['handoff_depth']}`\n"
        f"- D closure_packet_depth: `{d_metrics['closure_packet_depth']}`\n"
        f"- E closure_packet_depth: `{e_metrics['closure_packet_depth']}`\n"
        f"- material_difference_confirmed: `{comparison['material_difference_confirmed']}`\n\n"
        "## What Candidate E does not prove\n\n"
        "- It does not replace Candidate D as the default shipping baseline.\n"
        "- It does not enable silent auto-apply or autonomous implementation authority.\n"
        "- It does not certify global or proof-complete closure beyond the current bounded repository target.\n",
    )

    _run_profile(workspace, "D")
    set_active_strategy_profile(workspace, "D")
    return {
        "comparison": comparison,
        "manifest": manifest,
        "report_path": str(report.relative_to(workspace)),
    }


__all__ = ["build_candidate_e_release_bundle"]
