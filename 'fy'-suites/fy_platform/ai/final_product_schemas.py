"""Final product schemas for fy_platform.ai."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.evolution_contract_pack import canonical_schema_payloads
from fy_platform.ai.final_product_schema_catalog import legacy_schema_payloads
from fy_platform.ai.workspace import utc_now, workspace_root, write_json


def export_contract_schemas(root: Path | None = None) -> dict[str, Any]:
    """Export contract schemas."""
    workspace = workspace_root(root)
    out_dir = workspace / "docs" / "platform" / "schemas"
    internal_out_dir = workspace / "internal" / "docs" / "platform" / "schemas"
    out_dir.mkdir(parents=True, exist_ok=True)
    internal_out_dir.mkdir(parents=True, exist_ok=True)

    legacy = legacy_schema_payloads()
    canonical = canonical_schema_payloads(workspace)
    schema_payloads = {**legacy, **canonical}
    written: list[str] = []
    for name, payload in schema_payloads.items():
        path = out_dir / name
        write_json(path, payload)
        write_json(internal_out_dir / path.name, payload)
        written.append(str(path.relative_to(workspace)))
    return {
        "schema_version": "fy.schema-export.v1",
        "generated_at": utc_now(),
        "schema_count": len(written),
        "written_paths": written,
        "legacy_schema_count": len(legacy),
        "canonical_evolution_schema_count": len(canonical),
    }
