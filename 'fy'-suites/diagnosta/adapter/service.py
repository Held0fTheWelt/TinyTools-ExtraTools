"""Service helpers for diagnosta.adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from diagnosta.tools.analysis import build_readiness_bundle, write_latest_reports
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DiagnostaAdapter(BaseSuiteAdapter):
    """Adapter implementation for Diagnosta workflows."""

    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        super().__init__("diagnosta", root)

    def diagnose(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def readiness_case(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def blocker_graph(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def audit(self, target_repo_root: str) -> dict[str, Any]:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, _ = self._start_run("audit", target)
        try:
            bundle = build_readiness_bundle(self.root, target)
            written_roles = write_latest_reports(self.root, bundle)
            payload = {**bundle, "written_roles": written_roles}
            summary_md = "\n".join(
                [
                    "# Diagnosta Audit",
                    "",
                    bundle["readiness_case"]["summary"],
                    "",
                    f"- readiness_status: `{bundle['readiness_case']['readiness_status']}`",
                    f"- blocker_count: `{len(bundle['blocker_graph']['nodes'])}`",
                    f"- residue_count: `{len(bundle['residue_ledger']['items'])}`",
                    "",
                ]
            ) + "\n"
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=summary_md,
                role_prefix="diagnosta_audit",
            )
            for role_name, mapping in written_roles.items():
                for format_name, rel_path in mapping.items():
                    if not rel_path:
                        continue
                    fmt = "json" if format_name == "json_path" else "md"
                    artifact_payload = bundle[role_name] if fmt == "json" else None
                    self.registry.record_artifact(
                        suite=self.suite,
                        run_id=run_id,
                        format=fmt,
                        role=role_name,
                        path=rel_path,
                        payload=artifact_payload,
                    )
            self._finish_run(
                run_id,
                "ok",
                {
                    "readiness_status": bundle["readiness_case"]["readiness_status"],
                    "blocker_count": len(bundle["blocker_graph"]["nodes"]),
                    "residue_count": len(bundle["residue_ledger"]["items"]),
                    "active_profile": bundle["active_strategy_profile"]["active_profile"],
                },
            )
            return {
                "ok": True,
                "suite": self.suite,
                "run_id": run_id,
                **payload,
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", {"error": str(exc)})
            return {
                "ok": False,
                "suite": self.suite,
                "run_id": run_id,
                "error": str(exc),
            }

    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        payload = super().compare_runs(left_run_id, right_run_id)
        if not payload.get("ok"):
            return payload
        left_case = None
        right_case = None
        left_deep = None
        right_deep = None
        left_handoff = None
        right_handoff = None
        for artifact in self.registry.artifacts_for_run(left_run_id):
            artifact_payload = self.registry.artifact_payload(artifact["artifact_id"])
            if artifact["role"] == "readiness_case" and artifact_payload:
                left_case = artifact_payload
            elif artifact["role"] == "deep_synthesis" and artifact_payload:
                left_deep = artifact_payload
            elif artifact["role"] == "handoff_packet" and artifact_payload:
                left_handoff = artifact_payload
        for artifact in self.registry.artifacts_for_run(right_run_id):
            artifact_payload = self.registry.artifact_payload(artifact["artifact_id"])
            if artifact["role"] == "readiness_case" and artifact_payload:
                right_case = artifact_payload
            elif artifact["role"] == "deep_synthesis" and artifact_payload:
                right_deep = artifact_payload
            elif artifact["role"] == "handoff_packet" and artifact_payload:
                right_handoff = artifact_payload
        if left_case and right_case:
            payload["profile_depth_delta"] = {
                "active_profile_changed": left_case.get("active_profile") != right_case.get("active_profile"),
                "profile_execution_lane_changed": left_case.get("profile_execution_lane") != right_case.get("profile_execution_lane"),
                "profile_behavior_depth_changed": left_case.get("profile_behavior_depth") != right_case.get("profile_behavior_depth"),
                "planning_horizon_delta": int(right_case.get("planning_horizon") or 0) - int(left_case.get("planning_horizon") or 0),
            }
        if left_deep and right_deep:
            payload["diagnosta_depth_delta"] = {
                "blocker_cluster_delta_count": len(right_deep.get("blocker_clusters") or []) - len(left_deep.get("blocker_clusters") or []),
                "guarantee_gap_cluster_delta_count": len(right_deep.get("guarantee_gap_clusters") or []) - len(left_deep.get("guarantee_gap_clusters") or []),
                "next_wave_delta_count": len(right_deep.get("next_wave_plan") or []) - len(left_deep.get("next_wave_plan") or []),
            }
        if left_handoff and right_handoff:
            payload["handoff_depth_delta"] = {
                "depth_changed": left_handoff.get("depth") != right_handoff.get("depth"),
                "sequencing_hint_delta_count": len(right_handoff.get("sequencing_hints") or []) - len(left_handoff.get("sequencing_hints") or []),
                "grouped_obligation_delta_count": len(right_handoff.get("grouped_obligations") or []) - len(left_handoff.get("grouped_obligations") or []),
            }
        return payload
