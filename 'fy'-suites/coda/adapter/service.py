"""Service helpers for coda.adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from coda.tools.assembly import build_closure_bundle, write_latest_reports
from fy_platform.ai.base_adapter import BaseSuiteAdapter


class CodaAdapter(BaseSuiteAdapter):
    """Adapter implementation for Coda workflows."""

    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        super().__init__("coda", root)

    def assemble(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def closure_pack(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def bundle(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def residue_report(self, target_repo_root: str) -> dict[str, Any]:
        return self.audit(target_repo_root)

    def audit(self, target_repo_root: str) -> dict[str, Any]:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, _ = self._start_run("audit", target)
        try:
            bundle = build_closure_bundle(self.root, target)
            written_roles = write_latest_reports(self.root, bundle)
            payload = {**bundle, "written_roles": written_roles}
            summary_md = "\n".join(
                [
                    "# Coda Closure Pack",
                    "",
                    bundle["closure_pack"]["summary"],
                    "",
                    f"- status: `{bundle['closure_pack']['status']}`",
                    f"- obligation_count: `{len(bundle['closure_pack']['obligations'])}`",
                    f"- required_test_count: `{len(bundle['closure_pack']['required_tests'])}`",
                    f"- required_doc_count: `{len(bundle['closure_pack']['required_docs'])}`",
                    f"- review_acceptance_count: `{len(bundle['closure_pack']['review_acceptances'])}`",
                    f"- residue_count: `{len(bundle['residue_ledger']['items'])}`",
                    "",
                ]
            ) + "\n"
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=summary_md,
                role_prefix="coda_closure_pack",
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
                    "status": bundle["closure_pack"]["status"],
                    "obligation_count": len(bundle["closure_pack"]["obligations"]),
                    "required_test_count": len(bundle["closure_pack"]["required_tests"]),
                    "required_doc_count": len(bundle["closure_pack"]["required_docs"]),
                    "review_acceptance_count": len(bundle["closure_pack"]["review_acceptances"]),
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
        left_pack = None
        right_pack = None
        for artifact in self.registry.artifacts_for_run(left_run_id):
            if artifact["role"] == "closure_pack":
                left_pack = self.registry.artifact_payload(artifact["artifact_id"])
                break
        for artifact in self.registry.artifacts_for_run(right_run_id):
            if artifact["role"] == "closure_pack":
                right_pack = self.registry.artifact_payload(artifact["artifact_id"])
                break
        if left_pack and right_pack:
            payload["closure_pack_delta"] = {
                "status_changed": left_pack.get("status") != right_pack.get("status"),
                "obligation_delta_count": len(right_pack.get("obligations") or [])
                - len(left_pack.get("obligations") or []),
                "required_test_delta_count": len(right_pack.get("required_tests") or [])
                - len(left_pack.get("required_tests") or []),
                "required_doc_delta_count": len(right_pack.get("required_docs") or [])
                - len(left_pack.get("required_docs") or []),
                "accepted_review_delta_count": len(right_pack.get("review_acceptances") or [])
                - len(left_pack.get("review_acceptances") or []),
                "affected_surface_delta_count": len(right_pack.get("affected_surfaces") or [])
                - len(left_pack.get("affected_surfaces") or []),
                "grouped_obligation_delta_count": len(right_pack.get("grouped_obligations") or [])
                - len(left_pack.get("grouped_obligations") or []),
                "wave_packet_delta_count": len(right_pack.get("wave_packets") or [])
                - len(left_pack.get("wave_packets") or []),
                "auto_preparation_delta_count": len(right_pack.get("auto_preparation_packets") or [])
                - len(left_pack.get("auto_preparation_packets") or []),
                "packet_depth_changed": left_pack.get("packet_depth") != right_pack.get("packet_depth"),
                "profile_execution_lane_changed": left_pack.get("profile_execution_lane") != right_pack.get("profile_execution_lane"),
            }
        return payload
