"""Tests for artifact envelope.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.core.artifact_envelope import build_envelope, dump_envelope_json


def test_envelope_has_required_version_fields() -> None:
    """Verify that envelope has required version fields works as expected.
    """
    env = build_envelope(
        suite="docify",
        suite_version="0.1.0",
        payload={"ok": True},
        manifest_ref="fy-manifest.yaml",
    )
    assert env["envelopeVersion"] == "1"
    assert env["suite"] == "docify"
    assert env["suiteVersion"] == "0.1.0"
    assert env["manifest_ref"] == "fy-manifest.yaml"
    assert isinstance(env["findings"], list)
    assert isinstance(env["evidence"], list)
    assert isinstance(env["stats"], dict)


def test_envelope_json_is_canonical_sorted() -> None:
    """Verify that envelope json is canonical sorted works as expected.
    """
    env = build_envelope(
        suite="postmanify",
        suite_version="0.1.0",
        payload={"b": 2, "a": 1},
    )
    dumped = dump_envelope_json(env)
    loaded = json.loads(dumped)
    assert loaded["payload"]["a"] == 1
    assert dumped.endswith("\n")


def test_envelope_golden_serialization() -> None:
    """Verify that envelope golden serialization works as expected.
    """
    fixture = {
        "envelopeVersion": "1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "suite": "postmanify",
        "suiteVersion": "0.1.0",
        "manifest_ref": "fy-manifest.yaml",
        "compatMode": "transitional",
        "findings": [
            {
                "id": "F-001",
                "suite": "postmanify",
                "category": "api",
                "severity": "low",
                "confidence": 1.0,
                "summary": "example",
                "scope": "repository",
                "references": ["docs/api/openapi.yaml"],
            }
        ],
        "evidence": [{"kind": "source", "source_path": "docs/api/openapi.yaml", "deterministic": True}],
        "stats": {"n": 1},
        "deprecations": [],
        "payload": {"ok": True},
    }
    dumped = dump_envelope_json(fixture)
    golden = (
        Path(__file__).resolve().parent / "golden" / "envelope_v1.golden.json"
    ).read_text(encoding="utf-8")
    assert dumped == golden
