"""
Invariant: no bytecode paths are tracked under the Contractify hub (ZIP
/ export hygiene).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_CONTRACTIFY_PREFIX = "'fy'-suites/contractify"


def _repo_root() -> Path:
    """Repo root.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[4]


def test_tracked_contractify_paths_exclude_bytecode() -> None:
    """Verify that tracked contractify paths exclude bytecode works as
    expected.

    Control flow branches on the parsed state rather than relying on one
    linear path.
    """
    repo = _repo_root()
    marker = repo / "pyproject.toml"
    # Branch on not marker.is_file() so test_tracked_contractify_paths_exclude_bytecode
    # only continues along the matching state path.
    if not marker.is_file():
        pytest.skip("not a monorepo checkout")
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", _CONTRACTIFY_PREFIX],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    # Branch on proc.returncode != 0 so test_tracked_contractify_paths_exclude_bytecode
    # only continues along the matching state path.
    if proc.returncode != 0:
        pytest.skip("git ls-files unavailable")
    raw = proc.stdout.decode("utf-8", errors="replace")
    paths = [p for p in raw.split("\0") if p]
    norm = [p.replace("\\", "/") for p in paths]
    bad = [p for p in norm if "__pycache__" in p or p.endswith(".pyc") or p.endswith(".pyo")]
    assert not bad, f"tracked bytecode paths under {_CONTRACTIFY_PREFIX}: {bad}"
