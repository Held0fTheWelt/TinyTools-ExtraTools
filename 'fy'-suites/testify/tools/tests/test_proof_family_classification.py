"""Tests for sharper proof-family classification in Testify exports."""
from __future__ import annotations

import json
from pathlib import Path

from testify.tools.coda_exports import build_test_obligation_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_warning_only_and_linked_claims_do_not_create_blocker_gap(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "testify" / "reports" / "testify_audit.json",
        {
            "summary": {"finding_count": 0, "warning_count": 1},
            "findings": [],
            "warnings": ["frontend workflow is bundled elsewhere"],
        },
    )
    _write_json(
        tmp_path / "testify" / "generated" / "repo" / "testify-run" / "evolution_graph" / "claim_proof_status.json",
        {"linked_claims": [{"claim_id": "claim-1", "workflow_path": ".github/workflows/ci.yml"}]},
    )
    manifest = build_test_obligation_manifest(tmp_path)
    assert manifest["proof_family_status"]["blocker_gap_count"] == 0
    assert manifest["proof_family_status"]["warning_gap_count"] == 1
    assert len(manifest["required_tests"]) == 2
    assert all(item["blocking"] is False for item in manifest["required_tests"])
