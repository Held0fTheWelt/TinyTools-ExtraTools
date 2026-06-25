"""Coda export freshness tests for Testify."""
from __future__ import annotations

import json
from pathlib import Path

from testify.tools.coda_exports import build_test_obligation_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_coda_export_prefers_current_report_over_stale_generated_findings(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "testify" / "reports" / "testify_audit.json",
        {
            "summary": {"finding_count": 0, "warning_count": 1},
            "findings": [],
            "warnings": ["current warning"],
        },
    )
    _write_json(
        tmp_path
        / "testify"
        / "generated"
        / "target-repo-z"
        / "testify-z"
        / "evolution_graph"
        / "proof_report.json",
        {
            "findings": [
                {
                    "id": "STALE-FINDING",
                    "severity": "high",
                    "summary": "stale proof finding",
                }
            ],
            "warnings": ["stale warning"],
        },
    )
    _write_json(
        tmp_path
        / "testify"
        / "generated"
        / "target-repo-z"
        / "testify-z"
        / "evolution_graph"
        / "claim_proof_status.json",
        {
            "linked_claims": [{"claim_id": "current-claim", "workflow_path": ".github/workflows/ci.yml"}],
        },
    )

    manifest = build_test_obligation_manifest(tmp_path)

    assert manifest["obligations"] == []
    assert [item["summary"] for item in manifest["required_tests"]] == [
        "current warning",
        "Keep proof linkage healthy for claim `current-claim`.",
    ]
