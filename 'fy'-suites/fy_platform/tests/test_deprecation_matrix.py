"""Tests for deprecation matrix.

"""
from __future__ import annotations

import json
from pathlib import Path


def test_wave1_deprecation_matrix_has_active_entries() -> None:
    """Verify that wave1 deprecation matrix has active entries works as
    expected.
    """
    root = Path(__file__).resolve().parents[1]
    matrix = root / "deprecation_matrix.wave1.json"
    assert matrix.is_file()
    # Read and normalize the input data before
    # test_wave1_deprecation_matrix_has_active_entries branches on or transforms it
    # further.
    data = json.loads(matrix.read_text(encoding="utf-8"))
    assert data["version"] == "1"
    entries = data.get("entries", [])
    assert isinstance(entries, list)
    assert entries
    ids = {e["id"] for e in entries if isinstance(e, dict) and "id" in e}
    assert "DOCIFY-LEGACY-FALLBACK-001" in ids
    assert "POSTMANIFY-LEGACY-NAME-001" in ids
    assert "CONTRACTIFY-LEGACY-FALLBACK-001" in ids
