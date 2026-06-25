from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.final_product_schemas import export_contract_schemas


def test_export_contract_schemas_writes_grouped_legacy_catalog(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "internal").mkdir()
    result = export_contract_schemas(tmp_path)
    assert result["legacy_schema_count"] >= 10
    readiness = tmp_path / "docs" / "platform" / "schemas" / "readiness_case.schema.json"
    payload = json.loads(readiness.read_text(encoding="utf-8"))
    assert payload["title"] == "ReadinessCase"
    assert payload["schema_version"] == "fy.readiness-case.schema.v1"
