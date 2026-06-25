from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from usabilify.tools.canonical_graph import persist_usabilify_graph


SURFACE_DIR_NAMES = {"templates", "static", "assets", "ui", "frontend", "docs"}
SURFACE_SUFFIXES = {".html", ".css", ".js", ".jsx", ".tsx", ".md"}


def _surface_summary(path: Path) -> str:
    name = path.name.lower()
    if path.suffix == ".html" or "template" in path.parts:
        return "Template or page surface that shapes the user-facing experience."
    if path.suffix in {".css", ".js", ".jsx", ".tsx"}:
        return "Interactive or presentation asset that can affect usability."
    if name in {"readme.md", "overview.md"} or "docs" in path.parts:
        return "User-facing documentation surface."
    return "Observed user-facing repository surface."


def inspect_usability_surfaces(target: Path) -> dict:
    surfaces: list[dict[str, str]] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SURFACE_SUFFIXES:
            continue
        rel = path.relative_to(target)
        parts = {part.lower() for part in rel.parts}
        if not (parts & SURFACE_DIR_NAMES or rel.name.lower() == "readme.md"):
            continue
        if any(part in {".git", ".fydata", "__pycache__", ".pytest_cache", "node_modules"} for part in parts):
            continue
        surfaces.append({"path": rel.as_posix(), "summary": _surface_summary(rel)})
    buckets = {
        "templates": sum(1 for item in surfaces if "templates" in item["path"].split("/")),
        "static_assets": sum(1 for item in surfaces if Path(item["path"]).suffix in {".css", ".js", ".jsx", ".tsx"}),
        "docs": sum(1 for item in surfaces if item["path"].endswith(".md")),
    }
    next_steps = ["Review the highest-traffic templates and static assets for navigation, state clarity, and error recovery."]
    if not surfaces:
        next_steps = ["Add or point Usabilify at user-facing templates, static assets, docs, or frontend entrypoints."]
    return {
        "surface_count": len(surfaces),
        "surfaces": surfaces[:80],
        "buckets": buckets,
        "summary": f"Usabilify found {len(surfaces)} user-facing surfaces.",
        "next_steps": next_steps,
    }


def render_markdown(payload: dict) -> str:
    lines = ["# Usabilify Audit", "", f"- surface_count: {payload['surface_count']}", "", "## Buckets", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in payload["buckets"].items())
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in payload["next_steps"])
    return "\n".join(lines).strip() + "\n"


class UsabilifyAdapter(BaseSuiteAdapter):
    __test__ = False

    def __init__(self, root: Path | None = None) -> None:
        super().__init__("usabilify", root)

    def audit(self, target_repo_root: str) -> dict:
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run("audit", target)
        try:
            payload = inspect_usability_surfaces(target)
            payload["target_repo_id"] = tgt_id
            graph = persist_usabilify_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload["canonical_graph"] = {
                "unit_count": len(graph["unit_index"]["units"]),
                "relation_count": len(graph["relation_graph"]["relations"]),
                "artifact_count": graph["artifact_index"]["artifact_count"],
                "graph_dir": graph["graph_dir"],
                "export_dir": graph["export_dir"],
                "run_manifest_path": graph["written_paths"]["run_manifest"][1],
            }
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=render_markdown(payload), role_prefix="usabilify_audit")
            self._finish_run(run_id, "ok", {"surface_count": payload["surface_count"], "target_repo_id": tgt_id, "canonical_unit_count": payload["canonical_graph"]["unit_count"]})
            return {
                "ok": True,
                "suite": self.suite,
                "run_id": run_id,
                "surface_count": payload["surface_count"],
                "canonical_graph": payload["canonical_graph"],
                "summary": payload["summary"],
                "next_steps": payload["next_steps"],
                **paths,
            }
        except Exception as exc:
            self._finish_run(run_id, "failed", {"error": str(exc)})
            return {"ok": False, "suite": self.suite, "run_id": run_id, "reason": "audit_failed", "error": str(exc)}

    def inspect(self, query: str | None = None) -> dict:
        out = super().inspect(query)
        out["focus"] = ["templates", "static assets", "frontend entrypoints", "operator-facing docs"]
        out["suite_role"] = "Find observed user-facing surfaces and keep usability review grounded in files."
        return out

    def prepare_fix(self, finding_ids: list[str]) -> dict:
        out = super().prepare_fix(finding_ids)
        out["suggested_actions"] = [
            "prioritize confusing template or navigation surfaces",
            "add explicit empty, loading, and error states where user flow depends on runtime data",
            "rerun usabilify after interface changes to refresh the surface graph",
        ]
        return out

