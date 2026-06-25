"""Tests for sharper Despaghettify hotspot packet selection."""
from __future__ import annotations

import json
from pathlib import Path

from despaghettify.tools.coda_exports import build_insertion_surface_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_hotspot_packet_filters_import_mirror_paths(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {
            "file_spikes": [
                {
                    "path": "mvpify/imports/fy-suites-x/normalized/source_tree/diagnosta/tools/analysis.py",
                    "line_count": 700,
                    "severity": "high",
                },
                {
                    "path": "fy_platform/ai/adapter_commands.py",
                    "line_count": 440,
                    "severity": "medium",
                },
            ],
            "function_spikes": [],
        },
    )
    report = build_insertion_surface_report(tmp_path)
    assert all(
        not item["path"].startswith("mvpify/imports/")
        for item in report["affected_surfaces"]
    )
    packet = report["hotspot_decision_packet"]
    assert all(
        not str(item.get("source_path") or "").startswith("mvpify/imports/")
        for item in packet["blocking_hotspots"]
    )


def test_hotspot_packet_packetizes_closed_wave_support_helpers(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "despaghettify" / "reports" / "latest_check_with_metrics.json",
        {
            "file_spikes": [
                {"path": "contractify/tools/runtime_mvp_spine.py", "line_count": 500, "severity": "high"},
                {"path": "contractify/tools/runtime_mvp_spine_contracts_d.py", "line_count": 364, "severity": "low"},
            ],
            "function_spikes": [
                {"path": "documentify/tools/track_engine.py", "name": "generate_track_bundle", "line_span": 146, "severity": "medium"},
                {"path": "fy_platform/ai/evidence_registry/registry.py", "name": "sync_records", "line_span": 120, "severity": "medium"},
            ],
            "ownership_hotspots": [
                {"path": "fy_platform/ai/final_product_schema_catalog.py", "issue": "mixed_responsibility_module", "severity": "high"},
            ],
        },
    )
    report = build_insertion_surface_report(tmp_path)
    packet = report["hotspot_decision_packet"]
    assert [item["source_path"] for item in packet["blocking_hotspots"]] == ["contractify/tools/runtime_mvp_spine.py", "documentify/tools/track_engine.py"]
    assert any(item["source_path"] == "fy_platform/ai/evidence_registry/registry.py" for item in packet["non_blocking_hotspots"])
    assert any(item["source_path"] == "fy_platform/ai/final_product_schema_catalog.py" for item in packet["non_blocking_hotspots"])
