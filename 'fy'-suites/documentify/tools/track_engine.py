"""Documentify repository-level track compiler.

The track engine turns graph-backed suite evidence plus repository
context into layered documentation outputs for humans and AI consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from documentify.tools.document_builder import ROLE_MAP, collect_repository_context
from documentify.tools.graph_inputs import ALL_GRAPH_SUITES, build_suite_graph_context
from documentify.tools.self_hosting_views import build_tracking_context
from documentify.tools.track_audience_sections import (
    _ai_read_bundle,
    _docs_site_blueprint,
    _easy_doc,
    _operations_and_risk_summary_markdown,
    _role_doc,
    _status_page,
    _technical_doc,
)
from documentify.tools.track_evidence_sections import (
    _broad_suite_participation_markdown,
    _contracts_markdown,
    _coverage_matrix_markdown,
    _evidence_family_matrix_markdown,
    _evidence_gap_markdown,
    _evidence_status_markdown,
    _governance_reference_markdown,
    _mvp_import_reference_markdown,
    _self_hosting_evidence_markdown,
    _self_hosting_health_markdown,
    _stale_report_markdown,
    _tracking_markdown,
)
from fy_platform.ai.workspace import workspace_root

try:
    from templatify.tools.template_render import render_with_header
except Exception:  # pragma: no cover
    render_with_header = None


def _render_template_or_fallback(family: str, name: str, context: dict[str, object], fallback: str) -> str:
    """Render template output when Templatify is available."""
    if render_with_header is None:
        return fallback
    try:
        ws = workspace_root(Path(__file__))
        rendered, _record = render_with_header(ws, family, name, context)
        return rendered
    except Exception:
        return fallback


def _template_context(context: dict[str, Any], graph_inputs: dict[str, Any]) -> dict[str, str]:
    return {
        "services_csv": ", ".join(context["services"]) or "no detected services",
        "docs_dirs_csv": ", ".join(context["docs_dirs"]) or "none",
        "workflows_csv": ", ".join(context["workflows"]) or "none",
        "service_lines": "".join(f"- `{svc}/`\n" for svc in context["services"]) or "- none\n",
        "workflow_lines": "".join(f"- `{wf}`\n" for wf in context["workflows"]) or "- none\n",
        "key_doc_lines": "".join(f"- `{doc}`\n" for doc in context["key_docs"]) or "- none\n",
        "graph_summary": graph_inputs["shared_evidence_mode"],
    }


def _write_primary_docs(out_dir: Path, repo_root: Path, tpl_context: dict[str, str], context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> list[str]:
    generated: list[str] = []
    easy = out_dir / "easy" / "OVERVIEW.md"
    easy.parent.mkdir(parents=True, exist_ok=True)
    easy_text = _render_template_or_fallback("documentify", "easy_overview", tpl_context, _easy_doc(context, graph_inputs, tracking, repo_root))
    if "self-hosting" not in easy_text.lower() and repo_root.resolve() == workspace_root(Path(__file__)).resolve():
        easy_text += f"\nThis repository is also self-hosting: **{tracking['active_suite_count']} active suites** currently leave real tracking signals across the shared fy layers.\n"
    if graph_inputs["family_rows"] and "How this is governed" not in easy_text:
        family_names = ", ".join(row["family"] for row in graph_inputs["family_rows"] if row["linked_claim_count"] > 0) or ", ".join(row["family"] for row in graph_inputs["family_rows"])
        easy_text += "\n## How this is governed\n\n" + f"The current graph-backed slice is governed across these linked families: **{family_names}**.\n"
    easy.write_text(easy_text, encoding="utf-8")
    generated.append(easy.relative_to(out_dir).as_posix())

    technical = out_dir / "technical" / "SYSTEM_REFERENCE.md"
    technical.parent.mkdir(parents=True, exist_ok=True)
    technical.write_text(_render_template_or_fallback("documentify", "technical_reference", tpl_context, _technical_doc(context, graph_inputs)), encoding="utf-8")
    generated.append(technical.relative_to(out_dir).as_posix())

    track_files = [
        ("technical/COVERAGE_MATRIX.md", _coverage_matrix_markdown(graph_inputs)),
        ("technical/EVIDENCE_FAMILY_MATRIX.md", _evidence_family_matrix_markdown(graph_inputs)),
        ("technical/GOVERNANCE_REFERENCE.md", _governance_reference_markdown(graph_inputs)),
        ("technical/EVIDENCE_STATUS.md", _evidence_status_markdown(graph_inputs)),
        ("technical/DOCS_SITE_BLUEPRINT.md", _docs_site_blueprint(context)),
        ("technical/BROAD_SUITE_PARTICIPATION.md", _broad_suite_participation_markdown(graph_inputs)),
        ("technical/MVP_IMPORT_REFERENCE.md", _mvp_import_reference_markdown(graph_inputs)),
        ("technical/SELF_HOSTING_TRACKING.md", _tracking_markdown(tracking)),
        ("technical/SELF_HOSTING_CONTRACTS.md", _contracts_markdown(graph_inputs)),
        ("technical/SELF_HOSTING_EVIDENCE.md", _self_hosting_evidence_markdown(graph_inputs, tracking)),
        ("status/SELF_HOSTING_HEALTH.md", _self_hosting_health_markdown(graph_inputs, tracking)),
        ("status/STALE_REPORT.md", _stale_report_markdown(graph_inputs)),
        ("status/EVIDENCE_GAPS.md", _evidence_gap_markdown(graph_inputs)),
        ("status/OPERATIONS_AND_RISK_SUMMARY.md", _operations_and_risk_summary_markdown(graph_inputs)),
        ("status/MOST_RECENT_NEXT_STEPS.md", _status_page(context, graph_inputs, tracking)),
    ]
    for rel_name, content in track_files:
        path = out_dir / rel_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        generated.append(path.relative_to(out_dir).as_posix())
    return generated


def _write_role_docs(out_dir: Path, repo_root: Path, context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any]) -> list[str]:
    generated: list[str] = []
    for role in ROLE_MAP:
        role_path = out_dir / f"role-{role}" / "README.md"
        role_path.parent.mkdir(parents=True, exist_ok=True)
        role_path.write_text(_role_doc(role, context, graph_inputs, tracking, repo_root), encoding="utf-8")
        generated.append(role_path.relative_to(out_dir).as_posix())
    return generated


def _write_ai_read_bundle(out_dir: Path, tpl_context: dict[str, str], context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any], repo_root: Path) -> list[str]:
    ai_read = _ai_read_bundle(context, repo_root, graph_inputs, tracking)
    ai_dir = out_dir / "ai-read"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "bundle.json").write_text(json.dumps(ai_read, indent=2), encoding="utf-8")
    fallback_md = "# AI Read Bundle\n\n" + "".join(f"## {chunk['title']}\n\n{chunk['text']}\n\n" for chunk in ai_read["chunks"])
    (ai_dir / "bundle.md").write_text(_render_template_or_fallback("documentify", "ai_read", tpl_context, fallback_md), encoding="utf-8")
    return [(ai_dir / "bundle.json").relative_to(out_dir).as_posix(), (ai_dir / "bundle.md").relative_to(out_dir).as_posix()]


def _write_manifest_and_index(out_dir: Path, maturity: str, context: dict[str, Any], graph_inputs: dict[str, Any], tracking: dict[str, Any], generated_files: list[str]) -> dict[str, Any]:
    manifest = {
        "maturity": maturity,
        "tracks": ["easy", "technical", *[f"role-{r}" for r in ROLE_MAP], "ai-read", "status"],
        "generated_files": generated_files,
        "context": context,
        "graph_inputs": {
            "shared_evidence_mode": graph_inputs["shared_evidence_mode"],
            "family_rows": graph_inputs["family_rows"],
            **{
                suite: {
                    "available": graph_inputs[suite]["available"],
                    "producer_run_id": graph_inputs[suite].get("producer_run_id", ""),
                    "unit_count": graph_inputs[suite].get("unit_count", 0),
                    "relation_count": graph_inputs[suite].get("relation_count", 0),
                    "artifact_count": graph_inputs[suite].get("artifact_count", 0),
                }
                for suite in ALL_GRAPH_SUITES
            },
        },
        "self_hosting_tracking": tracking,
        "template_engine": "templatify" if render_with_header is not None else "builtin-fallback",
    }
    manifest_path = out_dir / "document_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    generated_files.append(manifest_path.relative_to(out_dir).as_posix())
    index_path = out_dir / "INDEX.md"
    index_lines = ["# Documentify Index", "", f"- maturity: `{maturity}`", f"- template_engine: `{manifest['template_engine']}`", f"- graph_mode: `{manifest['graph_inputs']['shared_evidence_mode']}`", "", "## Tracks", ""]
    index_lines.extend(f"- `{track}`" for track in manifest["tracks"])
    index_lines.extend(["", "## Generated files", ""])
    index_lines.extend(f"- `{path}`" for path in generated_files)
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    generated_files.append(index_path.relative_to(out_dir).as_posix())
    manifest["generated_count"] = len(generated_files)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def generate_track_bundle(repo_root: Path, out_dir: Path, maturity: str = "evidence-fill") -> dict[str, Any]:
    """Generate the full repository track bundle."""
    out_dir.mkdir(parents=True, exist_ok=True)
    context = collect_repository_context(repo_root)
    graph_inputs = build_suite_graph_context(repo_root)
    tracking = build_tracking_context(repo_root)
    tpl_context = _template_context(context, graph_inputs)
    generated_files = _write_primary_docs(out_dir, repo_root, tpl_context, context, graph_inputs, tracking)
    generated_files.extend(_write_role_docs(out_dir, repo_root, context, graph_inputs, tracking))
    generated_files.extend(_write_ai_read_bundle(out_dir, tpl_context, context, graph_inputs, tracking, repo_root))
    return _write_manifest_and_index(out_dir, maturity, context, graph_inputs, tracking, generated_files)
