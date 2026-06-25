"""Tests for compatibility matrix.

"""
from __future__ import annotations

import json
from pathlib import Path


def test_wave1_baseline_compatibility_matrix_exists() -> None:
    """Verify that wave1 baseline compatibility matrix exists works as
    expected.
    """
    root = Path(__file__).resolve().parents[1]
    matrix = root / "compatibility_matrix.wave1_baseline.json"
    assert matrix.is_file()
    # Read and normalize the input data before
    # test_wave1_baseline_compatibility_matrix_exists branches on or transforms it
    # further.
    data = json.loads(matrix.read_text(encoding="utf-8"))
    assert data["matrixVersion"] == "1"
    assert "docify" in data["suites"]
    assert "postmanify" in data["suites"]
    assert "operational_surfaces" in data
    assert "command_flag_surfaces" in data["operational_surfaces"]
    assert "default_filenames" in data["operational_surfaces"]
