"""Evidence loading helpers for Diagnosta.

These helpers stay deliberately bounded. They only read existing supporting-suite
artifacts or trigger the matching bounded export when the suite already owns that
artifact surface.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contractify.tools.coda_exports import emit_contract_obligation_manifest
from despaghettify.tools.coda_exports import emit_insertion_surface_report
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from testify.tools.coda_exports import emit_test_obligation_manifest


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    return _load_json(path) if path.is_file() else None


def _safe_emit(emitter, workspace: Path) -> dict[str, Any] | None:
    try:
        return emitter(workspace)
    except FileNotFoundError:
        return None


def load_supporting_evidence(workspace: Path) -> dict[str, Any]:
    """Load the bounded supporting evidence used by Diagnosta."""
    contractify = _safe_emit(emit_contract_obligation_manifest, workspace)
    testify = _safe_emit(emit_test_obligation_manifest, workspace)
    despag = _safe_emit(emit_insertion_surface_report, workspace)
    dockerify_path = workspace / "dockerify" / "reports" / "dockerify_audit.json"
    securify_path = workspace / "securify" / "reports" / "securify_audit.json"
    mvpify_inventory_path = workspace / "mvpify" / "reports" / "mvpify_import_inventory.json"
    mvpify_handoff_path = workspace / "mvpify" / "reports" / "mvpify_diagnosta_handoff.json"
    return {
        "active_strategy_profile": strategy_runtime_metadata(workspace),
        "contractify": contractify,
        "testify": testify,
        "despaghettify": despag,
        "dockerify": _load_optional_json(dockerify_path),
        "securify": _load_optional_json(securify_path),
        "mvpify_import_inventory": _load_optional_json(mvpify_inventory_path),
        "mvpify_handoff": _load_optional_json(mvpify_handoff_path),
        "evidence_sources": [
            source
            for source in [
                (contractify or {}).get(
                    "written_paths", {}
                ).get("json_path", "contractify/reports/latest_coda_obligation_manifest.json")
                if contractify
                else None,
                (testify or {}).get(
                    "written_paths", {}
                ).get("json_path", "testify/reports/latest_coda_test_obligation_manifest.json")
                if testify
                else None,
                (despag or {}).get(
                    "written_paths", {}
                ).get("json_path", "despaghettify/reports/latest_coda_insertion_surface_report.json")
                if despag
                else None,
            ]
            if source
        ],
    }


__all__ = ["load_supporting_evidence"]
