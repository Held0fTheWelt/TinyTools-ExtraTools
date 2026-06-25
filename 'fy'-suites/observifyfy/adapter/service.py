"""Service helpers for observifyfy.adapter."""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from observifyfy.tools.ai_support import build_ai_context
from observifyfy.tools.canonical_graph import persist_observifyfy_graph
from observifyfy.tools.hub_cli import run_audit
from observifyfy.tools.repo_paths import fy_observifyfy_root
from observifyfy.tools.scanner import scan_workspace


class ObservifyfyAdapter(BaseSuiteAdapter):
    """Adapter implementation for observifyfy workflows."""

    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        super().__init__("observifyfy", root)
        self.hub_dir = fy_observifyfy_root(self.root)
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "reports").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "state").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "generated").mkdir(parents=True, exist_ok=True)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, _ = self._start_run("audit", target)
        try:
            result = run_audit(target)
            inventory = result["inventory"]
            next_steps = result["next_steps"]
            diagnosta_signal = result.get("diagnosta_signal") or {}
            coda_signal = result.get("coda_signal") or {}
            payload = {
                "inventory": inventory,
                "next_steps": next_steps,
                "diagnosta_signal": diagnosta_signal,
                "coda_signal": coda_signal,
                "active_strategy_profile": diagnosta_signal.get(
                    "active_strategy_profile"
                )
                or strategy_runtime_metadata(self.root),
                "ai_context": build_ai_context(
                    inventory,
                    next_steps,
                    diagnosta_signal=diagnosta_signal,
                    coda_signal=coda_signal,
                ),
            }
            graph_bundle = persist_observifyfy_graph(
                workspace=self.root,
                repo_root=target,
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
            md = [
                "# Observifyfy Audit",
                "",
                f"- tracked suites: {inventory['existing_suite_count']}",
                (
                    f"- active_profile: `"
                    f"{payload['active_strategy_profile'].get('active_profile', 'D')}`"
                ),
                (
                    f"- diagnosta_readiness_status: `"
                    f"{(diagnosta_signal.get('readiness_case') or {}).get('readiness_status', 'unknown')}`"
                ),
                (
                    f"- coda_closure_status: `"
                    f"{(coda_signal.get('closure_pack') or {}).get('status', 'unknown')}`"
                ),
                (
                    f"- highest next step: "
                    f"{next_steps.get('highest_value_next_step', {}).get('recommended_action', 'none')}"
                ),
                "",
            ]
            paths = self._write_payload_bundle(
                run_id=run_id,
                run_dir=run_dir,
                payload=payload,
                summary_md="\n".join(md) + "\n",
                role_prefix="observifyfy_audit",
            )
            self._finish_run(
                run_id,
                "ok",
                {
                    "tracked_suites": inventory["existing_suite_count"],
                    "active_profile": payload["active_strategy_profile"].get(
                        "active_profile", "D"
                    ),
                },
            )
            return {
                "ok": True,
                "suite": self.suite,
                "run_id": run_id,
                "canonical_graph": payload["canonical_graph"],
                "active_strategy_profile": payload["active_strategy_profile"],
                "diagnosta_signal": diagnosta_signal,
                "coda_signal": coda_signal,
                "next_steps": next_steps,
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", {"error": str(exc)})
            return {"ok": False, "suite": self.suite, "run_id": run_id, "error": str(exc)}

    def inspect(self, query: str | None = None) -> dict:
        out = super().inspect(query)
        inv = scan_workspace(self.root)
        out["tracked_suite_count"] = inv["existing_suite_count"]
        out["internal_roots"] = inv["internal_roots"]
        return out

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out["suggested_actions"] = [
            "refresh internal docs routing under docs",
            "refresh internal ADR routing under docs/ADR",
            "run stale suites again and consolidate next steps",
        ]
        return out
