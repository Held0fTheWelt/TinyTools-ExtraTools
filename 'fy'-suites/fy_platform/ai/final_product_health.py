"""Final product health for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.final_product_catalog import (
    command_reference_payload,
    render_command_reference_markdown,
    render_suite_catalog_markdown,
    suite_catalog_payload,
)
from fy_platform.ai.final_product_schemas import export_contract_schemas
from fy_platform.ai.production_readiness import workspace_production_readiness
from fy_platform.ai.release_readiness import workspace_release_readiness
from fy_platform.ai.workspace import utc_now, workspace_root, write_json, write_text
from fy_platform.ai.workspace_status_site import build_workspace_status_site


def doctor_payload(root: Path | None = None) -> dict[str, Any]:
    """Doctor payload.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Read and normalize the input data before doctor_payload branches on or transforms
    # it further.
    workspace = workspace_root(root)
    release = workspace_release_readiness(workspace)
    production = workspace_production_readiness(workspace)
    status = build_workspace_status_site(workspace)
    catalog = suite_catalog_payload(workspace)
    top: list[str] = []
    top.extend(production.get("top_next_steps", []))
    # Branch on release.get('core_blocked_suites') so doctor_payload only continues
    # along the matching state path.
    if release.get("core_blocked_suites"):
        top.append("Focus first on blocked core suites before starting optional suite work.")
    # Branch on status.get('blocked_suite_count', 0) so doctor_payload only continues
    # along the matching state path.
    if status.get("blocked_suite_count", 0):
        top.append("Use the workspace status site to read each suite's most recent next steps in simple language.")
    # Branch on not top so doctor_payload only continues along the matching state path.
    if not top:
        top.append("The workspace looks healthy. Keep running self-audit, release-readiness, and production-readiness before outward release work.")
    return {
        "schema_version": "fy.doctor.v1",
        "generated_at": utc_now(),
        "ok": bool(release["ok"] and production["ok"]),
        "workspace_release": release,
        "workspace_production": production,
        "workspace_status": status,
        "catalog": catalog,
        "top_next_steps": top[:8],
    }


def render_doctor_markdown(payload: dict[str, Any]) -> str:
    """Render doctor markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        "# fy Doctor",
        "",
        "This page is the top-level health view for the current workspace.",
        "",
        f"- ok: `{str(payload['ok']).lower()}`",
        f"- workspace_ready: `{str(payload['workspace_release']['ok']).lower()}`",
        f"- production_ready: `{str(payload['workspace_production']['ok']).lower()}`",
        f"- catalog_suites: `{payload['catalog']['suite_count']}`",
        "",
        "## Top Next Steps",
        "",
    ]
    for step in payload.get("top_next_steps", []):
        lines.append(f"- {step}")
    lines.extend(["", "## Core blocked suites", ""])
    blocked = payload["workspace_release"].get("core_blocked_suites", [])
    if blocked:
        for suite in blocked:
            lines.append(f"- `{suite}`")
    else:
        lines.append("- none")
    return "\n".join(lines).strip() + "\n"


def final_release_bundle(root: Path | None = None) -> dict[str, Any]:
    """Final release bundle.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    catalog = suite_catalog_payload(workspace)
    command_reference = command_reference_payload(workspace)
    schemas = export_contract_schemas(workspace)
    doctor = doctor_payload(workspace)
    release = workspace_release_readiness(workspace)
    production = workspace_production_readiness(workspace)
    bundle = {
        "schema_version": "fy.final-release-bundle.v1",
        "generated_at": utc_now(),
        "workspace_root": str(workspace),
        "catalog": catalog,
        "command_reference": command_reference,
        "schemas": schemas,
        "doctor": doctor,
        "workspace_release": release,
        "workspace_production": production,
    }
    docs_dir = workspace / "docs" / "platform"
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(docs_dir / "suite_catalog.json", catalog)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(docs_dir / "SUITE_CATALOG.md", render_suite_catalog_markdown(catalog))
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(docs_dir / "command_reference.json", command_reference)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(docs_dir / "SUITE_COMMAND_REFERENCE.md", render_command_reference_markdown(command_reference))
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(docs_dir / "doctor.json", doctor)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(docs_dir / "DOCTOR.md", render_doctor_markdown(doctor))
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(docs_dir / "final_release_bundle.json", bundle)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    write_text(
        docs_dir / "FINAL_RELEASE_BUNDLE.md",
        "\n".join([
            "# fy Final Release Bundle",
            "",
            "This bundle captures the current suite catalog, command reference, schemas, doctor output, release readiness, and production readiness in one place.",
            "",
            f"- generated_at: `{bundle['generated_at']}`",
            f"- catalog_suites: `{catalog['suite_count']}`",
            f"- schemas_exported: `{schemas['schema_count']}`",
            f"- workspace_release_ok: `{str(release['ok']).lower()}`",
            f"- workspace_production_ok: `{str(production['ok']).lower()}`",
            "",
        ]),
    )
    return bundle
