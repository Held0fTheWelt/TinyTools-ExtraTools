"""Service helpers for mvpify.adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.workspace import write_json, write_text
from mvpify.tools.canonical_graph import persist_mvpify_graph
from mvpify.tools.hub_cli import run as run_mvpify


class MVPifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for mvpify workflows."""

    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        super().__init__("mvpify", root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run("audit", target)
        try:
            payload = run_mvpify(target, source_root=str(target))
            import_inventory = payload.get("import_inventory", {})
            plan = payload.get("plan", {})
            diagnosta_handoff = self._build_diagnosta_handoff(
                run_id=run_id,
                payload=payload,
            )
            payload["diagnosta_handoff"] = diagnosta_handoff
            summary_md = "\n".join(
                [
                    "# MVPify Audit",
                    "",
                    f"- target: `{target}`",
                    f"- import_source: `{import_inventory.get('source', '')}`",
                    f"- artifact_count: {import_inventory.get('artifact_count', 0)}",
                    f"- step_count: {len(plan.get('steps', []))}",
                    (
                        f"- highest_value_next_step: `"
                        f"{(plan.get('highest_value_next_step') or {}).get('suite', 'mvpify')}`"
                    ),
                    f"- diagnosta_readiness_status: `{diagnosta_handoff['readiness_status']}`",
                    f"- implementation_outcome: `{diagnosta_handoff['implementation_outcome']}`",
                    "",
                ]
            ) + "\n"
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=summary_md,
                role_prefix="mvpify_audit",
            )
            self._finish_run(
                run_id,
                "ok",
                {
                    "artifact_count": import_inventory.get("artifact_count", 0),
                    "step_count": len(plan.get("steps", [])),
                    "target_repo_id": tgt_id,
                    "implementation_outcome": diagnosta_handoff["implementation_outcome"],
                },
            )
            return {
                "ok": True,
                "suite": self.suite,
                "run_id": run_id,
                "artifact_count": import_inventory.get("artifact_count", 0),
                "step_count": len(plan.get("steps", [])),
                "diagnosta_handoff": diagnosta_handoff,
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", {"error": str(exc)})
            return {"ok": False, "suite": self.suite, "run_id": run_id, "error": str(exc)}

    def inspect(self, query: str | None = None) -> dict:
        out = super().inspect(query)
        out["suite_role"] = (
            "Import, normalize, mirror, and orchestrate prepared MVP bundles "
            "into the governed fy workspace."
        )
        out["focus"] = [
            "prepared MVP intake",
            "doc mirroring",
            "suite orchestration",
            "observifyfy-tracked import cycles",
        ]
        return out

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out["suggested_actions"] = [
            "normalize imported MVP surfaces into mvpify/imports/<id>/normalized",
            "mirror MVP docs into docs/MVPs/imports/<id> so implementation folders can later be removed",
            "handoff imported contracts to contractify import or legacy-import as needed",
            "refresh observifyfy after each MVP import cycle",
        ]
        return out

    def _build_diagnosta_handoff(
        self,
        *,
        run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        from diagnosta.adapter.service import DiagnostaAdapter

        diagnosta = DiagnostaAdapter(root=self.root)
        diagnosis = diagnosta.diagnose(str(self.root))
        import_inventory = payload.get("import_inventory") or {}
        plan = payload.get("plan") or {}
        readiness_status = (
            diagnosis.get("readiness_case") or {}
        ).get("readiness_status", "abstain_insufficient_evidence")
        if readiness_status == "bounded_ready_with_residue":
            outcome = "implementation_ready_with_residue"
        elif readiness_status == "not_ready":
            outcome = "not_ready"
        else:
            outcome = "not_ready_insufficient_evidence"
        handoff = {
            "schema_version": "fy.mvpify-diagnosta-handoff.v1",
            "import_id": (import_inventory.get("import_inventory") or import_inventory).get(
                "import_id",
                import_inventory.get("import_id", ""),
            ),
            "mvpify_run_id": run_id,
            "diagnosta_run_id": diagnosis.get("run_id", ""),
            "target_repo_root": str(self.root),
            "active_strategy_profile": diagnosis.get("active_strategy_profile") or {},
            "readiness_status": readiness_status,
            "implementation_outcome": outcome,
            "blocker_count": len(
                ((diagnosis.get("blocker_priority_report") or {}).get("priorities") or [])
            ),
            "blocked_claim_count": len(
                ((diagnosis.get("cannot_honestly_claim") or {}).get("blocked_claims") or [])
            ),
            "residue_count": len(
                ((diagnosis.get("residue_ledger") or {}).get("items") or [])
            ),
            "highest_value_next_step": plan.get("highest_value_next_step") or {},
            "import_context": {
                "artifact_count": import_inventory.get("artifact_count", 0),
                "source": import_inventory.get("source", ""),
                "suite_signals": (
                    (import_inventory.get("inventory") or {}).get("suite_signals") or []
                ),
            },
            "summary": (
                f"MVPify handed the imported target to Diagnosta and received "
                f"{readiness_status} / {outcome}."
            ),
            "next_steps": [
                "Review the Diagnosta readiness_case before scheduling implementation work.",
                "Use the blocker_priority_report to pick the next bounded implementation wave.",
                "Keep residue explicit when the import is not fully implementation-ready.",
            ],
            "diagnosta_paths": {
                "readiness_case": (
                    diagnosis.get("written_roles", {})
                    .get("readiness_case", {})
                    .get("json_path", "")
                ),
                "blocker_graph": (
                    diagnosis.get("written_roles", {})
                    .get("blocker_graph", {})
                    .get("json_path", "")
                ),
                "guarantee_gap_report": (
                    diagnosis.get("guarantee_gap_report", {})
                    .get("md_path", "")
                ),
            },
        }
        reports_root = self.root / "mvpify" / "reports"
        write_json(reports_root / "mvpify_diagnosta_handoff.json", handoff)
        write_text(
            reports_root / "mvpify_diagnosta_handoff.md",
            "\n".join(
                [
                    "# MVPify Diagnosta Handoff",
                    "",
                    handoff["summary"],
                    "",
                    f"- readiness_status: `{handoff['readiness_status']}`",
                    f"- implementation_outcome: `{handoff['implementation_outcome']}`",
                    f"- blocker_count: `{handoff['blocker_count']}`",
                    f"- residue_count: `{handoff['residue_count']}`",
                    "",
                ]
            )
            + "\n",
        )
        return handoff

    def import_bundle(self, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
        target = self.root.resolve()
        run_id, run_dir, tgt_id = self._start_run("import", target)
        try:
            payload = run_mvpify(self.root, mvp_zip=bundle_path)
            graph_bundle = persist_mvpify_graph(
                workspace=self.root,
                repo_root=self.root,
                run_id=run_id,
                payload=payload,
            )
            payload["canonical_graph"] = {
                "unit_count": len(graph_bundle["unit_index"]["units"]),
                "relation_count": len(graph_bundle["relation_graph"]["relations"]),
                "artifact_count": graph_bundle["artifact_index"]["artifact_count"],
                "graph_dir": graph_bundle["graph_dir"],
                "export_dir": graph_bundle["export_dir"],
                "run_manifest_path": graph_bundle["written_paths"]["run_manifest"][1],
            }
            diagnosta_handoff = self._build_diagnosta_handoff(
                run_id=run_id,
                payload=payload,
            )
            payload["diagnosta_handoff"] = diagnosta_handoff
            summary_md = "\n".join(
                [
                    "# MVPify Import",
                    "",
                    f"- bundle: `{bundle_path}`",
                    f"- import_id: `{payload.get('import_inventory', {}).get('import_id', '')}`",
                    f"- plan_step_count: {len((payload.get('plan') or {}).get('steps', []))}",
                    f"- canonical_unit_count: {len(graph_bundle['unit_index']['units'])}",
                    f"- diagnosta_readiness_status: `{diagnosta_handoff['readiness_status']}`",
                    f"- implementation_outcome: `{diagnosta_handoff['implementation_outcome']}`",
                    "",
                ]
            )
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md=summary_md,
                role_prefix="mvpify_import",
            )
            self._finish_run(
                run_id,
                "ok",
                {
                    "artifact_count": payload.get("import_inventory", {}).get(
                        "artifact_count", 0
                    ),
                    "step_count": len((payload.get("plan") or {}).get("steps", [])),
                    "target_repo_id": tgt_id,
                    "implementation_outcome": diagnosta_handoff[
                        "implementation_outcome"
                    ],
                },
            )
            return {
                "ok": True,
                "suite": self.suite,
                "run_id": run_id,
                "canonical_graph": payload["canonical_graph"],
                "diagnosta_handoff": diagnosta_handoff,
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", {"error": str(exc)})
            return {"ok": False, "suite": self.suite, "run_id": run_id, "error": str(exc)}
