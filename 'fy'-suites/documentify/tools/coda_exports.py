"""Coda-facing export surfaces for Documentify.

This module exports bounded documentation obligations from existing
Documentify manifests so Coda can attach documentation review surfaces to
closure packs.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now, write_json, write_text


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _latest_manifest(workspace: Path) -> Path | None:
    matches = sorted(glob.glob(str(workspace / "documentify/generated/*/documentify-*/document_manifest.json")))
    if matches:
        return Path(matches[-1])
    return None


def _closure_relevant_generated_doc(item: str) -> bool:
    normalized = str(item).strip()
    if not normalized:
        return False
    if normalized.startswith("status/"):
        return False
    if normalized.endswith(".json"):
        return False
    return True


def build_documentify_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Build bounded documentation obligations from Documentify manifest data."""
    manifest_path = _latest_manifest(workspace)
    if manifest_path is None:
        raise FileNotFoundError("No Documentify manifest was found.")
    payload = _load_json(manifest_path)
    tracks = [str(item) for item in list(payload.get("tracks") or [])]
    generated_files = [str(item) for item in list(payload.get("generated_files") or [])]
    generated_root = manifest_path.parent

    relevant_generated_files = [item for item in generated_files if _closure_relevant_generated_doc(item)]
    required_docs: list[dict[str, Any]] = []
    for item in relevant_generated_files[:12]:
        artifact_present = (generated_root / item).is_file()
        track = item.split("/", 1)[0] if "/" in item else item
        required_docs.append(
            {
                "doc_id": f"documentify:{item}",
                "suite": "documentify",
                "severity": "medium",
                "summary": f"Keep generated documentation track `{item}` aligned with the closure pack.",
                "path": item,
                "track": track,
                "source_kind": "generated_document",
                "artifact_present": artifact_present,
                "review_acceptance_candidate": artifact_present,
            }
        )

    obligations: list[dict[str, Any]] = []
    track_statuses: list[dict[str, Any]] = []
    for item in tracks[:8]:
        generated_for_track = [path for path in relevant_generated_files if path == item or path.startswith(f"{item}/")]
        generated_count = len(generated_for_track)
        satisfied_by_current_artifacts = generated_count > 0
        obligations.append(
            {
                "obligation_id": f"documentify-track:{item}",
                "suite": "documentify",
                "category": "documentation_track_alignment",
                "severity": "medium",
                "summary": f"Preserve the Documentify `{item}` track when landing the closure pack.",
                "source_paths": [item],
                "review_required": True,
                "track": item,
                "generated_file_count": generated_count,
                "satisfied_by_current_artifacts": satisfied_by_current_artifacts,
                "review_acceptance_candidate": satisfied_by_current_artifacts,
            }
        )
        track_statuses.append(
            {
                "track": item,
                "generated_file_count": generated_count,
                "generated": satisfied_by_current_artifacts,
            }
        )

    manifest = {
        "schema_version": "fy.documentify-coda-documentation-obligation-manifest.v1",
        "suite": "documentify",
        "generated_at": utc_now(),
        "source_report": str(manifest_path.relative_to(workspace)),
        "generated_root": str(generated_root.relative_to(workspace)),
        "tracks": tracks,
        "track_statuses": track_statuses,
        "obligations": obligations,
        "required_docs": required_docs,
        "summary": (
            f"Documentify exported {len(required_docs)} bounded required docs and "
            f"{len(obligations)} documentation-track obligations."
        ),
    }
    return manifest


def emit_documentify_obligation_manifest(workspace: Path) -> dict[str, Any]:
    """Write the latest Documentify documentation obligation manifest for Coda."""
    manifest = build_documentify_obligation_manifest(workspace)
    reports = workspace / "documentify" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest_coda_documentation_manifest.json"
    md_path = reports / "latest_coda_documentation_manifest.md"
    write_json(json_path, manifest)
    lines = [
        "# Documentify Coda Documentation Obligation Manifest",
        "",
        manifest["summary"],
        "",
        f"- required_doc_count: `{len(manifest['required_docs'])}`",
        f"- track_count: `{len(manifest['tracks'])}`",
        "",
    ]
    for item in manifest["required_docs"][:20]:
        lines.append(f"- `{item['path']}` — {item['summary']}")
    write_text(md_path, "\n".join(lines) + "\n")
    manifest["written_paths"] = {
        "json_path": str(json_path.relative_to(workspace)),
        "md_path": str(md_path.relative_to(workspace)),
    }
    write_json(json_path, manifest)
    return manifest


__all__ = ["build_documentify_obligation_manifest", "emit_documentify_obligation_manifest"]
