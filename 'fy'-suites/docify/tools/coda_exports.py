"""Coda-facing export surfaces for Docify.

This module exports bounded documentation obligations from Docify's existing
coverage baseline. It stays at the obligation layer and does not mutate code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, write_json, write_text

_BASELINE_PATH = Path("docify/baseline_docstring_coverage.json")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_stale_doc_path(path: str) -> bool:
    if not path:
        return False
    candidate = Path(path)
    if candidate.is_absolute() or path.startswith(".."):
        return True
    return path.startswith((
        "mvpify/imports/",
        "docs/MVPs/imports/",
        ".fydata/",
        "generated/",
        "examples/",
    ))


def _path_exists(workspace: Path, path: str) -> bool:
    return (workspace / path).is_file()


def build_docify_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Build bounded documentation obligations from Docify baseline data.

    Findings stay as documentation obligations. Parser issues become concrete
    required-doc follow-up items. This avoids double-counting the same Docify
    finding as both an obligation and a required document.
    """
    baseline_path = workspace / _BASELINE_PATH
    if not baseline_path.is_file():
        raise FileNotFoundError("No Docify baseline coverage file was found.")
    baseline = _load_json(baseline_path)
    findings = list(baseline.get("findings") or [])
    parse_errors = [str(item) for item in list(baseline.get("parse_errors") or [])]

    obligations: list[dict[str, Any]] = []
    required_docs: list[dict[str, Any]] = []
    for item in findings[:12]:
        path = str(item.get("path") or "")
        if not path or _is_stale_doc_path(path) or not _path_exists(workspace, path):
            continue
        name = str(item.get("name") or "<unknown>")
        summary = f"Improve docstrings or inline documentation for `{path}` / `{name}`."
        obligations.append(
            {
                "obligation_id": f"docify:{path}:{name}",
                "suite": "docify",
                "category": "documentation_quality",
                "severity": "medium",
                "summary": summary,
                "source_paths": [path],
                "review_required": True,
            }
        )

    parse_error_index = 0
    for item in parse_errors[:6]:
        candidate_path = str(item).split(":", 1)[0].strip()
        if candidate_path and (_is_stale_doc_path(candidate_path) or not _path_exists(workspace, candidate_path)):
            continue
        parse_error_index += 1
        required_docs.append(
            {
                "doc_id": f"docify-parse-error-{parse_error_index}",
                "suite": "docify",
                "severity": "high",
                "summary": f"Resolve documentation parser issue: {item}",
                "path": candidate_path if candidate_path and not _is_stale_doc_path(candidate_path) else "",
                "source_kind": "parse_error",
            }
        )

    manifest = {
        "schema_version": "fy.docify-coda-documentation-obligation-manifest.v1",
        "suite": "docify",
        "generated_at": utc_now(),
        "source_report": str(_BASELINE_PATH),
        "obligations": obligations,
        "required_docs": required_docs,
        "summary": (
            f"Docify exported {len(obligations)} documentation obligations and "
            f"{len(required_docs)} concrete required-doc follow-up item(s) from baseline coverage data."
        ),
    }
    return manifest


def emit_docify_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Write the latest Docify documentation obligation manifest for Coda."""
    manifest = build_docify_obligation_manifest(workspace)
    reports = workspace / "docify" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest_coda_documentation_manifest.json"
    md_path = reports / "latest_coda_documentation_manifest.md"
    write_json(json_path, manifest)
    lines = [
        "# Docify Coda Documentation Obligation Manifest",
        "",
        manifest["summary"],
        "",
        f"- obligation_count: `{len(manifest['obligations'])}`",
        f"- required_doc_count: `{len(manifest['required_docs'])}`",
        "",
    ]
    for item in manifest["obligations"][:20]:
        lines.append(f"- `{item['obligation_id']}` — {item['summary']}")
    for item in manifest["required_docs"][:20]:
        lines.append(f"- `{item['doc_id']}` — {item['summary']}")
    write_text(md_path, "\n".join(lines) + "\n")
    manifest["written_paths"] = {
        "json_path": str(json_path.relative_to(workspace)),
        "md_path": str(md_path.relative_to(workspace)),
    }
    write_json(json_path, manifest)
    return manifest


__all__ = ["build_docify_obligation_manifest", "emit_docify_obligation_manifest"]
