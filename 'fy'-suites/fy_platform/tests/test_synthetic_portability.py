"""Tests for synthetic portability.

"""
from __future__ import annotations

import json
from pathlib import Path

from docify.tools.python_documentation_audit import main as docify_audit_main
from fy_platform.core.project_resolver import resolve_project_root
from postmanify.tools import cli as postmanify_cli


def _fixture_root(name: str) -> Path:
    """Fixture root.

    Args:
        name: Primary name used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parents[1] / "fixtures" / name


def test_fixture_root_resolution_uses_manifest() -> None:
    """Verify that fixture root resolution uses manifest works as expected.
    """
    repo = _fixture_root("library_only")
    nested = repo / "src"
    resolved = resolve_project_root(start=nested)
    assert resolved == repo


def test_docify_runs_on_library_only_fixture(tmp_path: Path) -> None:
    """Verify that docify runs on library only fixture works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo = _fixture_root("library_only")
    out = tmp_path / "docify.json"
    env = tmp_path / "docify.envelope.json"
    code = docify_audit_main(
        [
            "--repo-root",
            str(repo),
            "--json",
            "--out",
            str(out),
            "--envelope-out",
            str(env),
            "--exit-zero",
        ]
    )
    assert code == 0
    assert out.is_file()
    assert env.is_file()


def test_postmanify_plan_runs_on_backend_fixture(monkeypatch, tmp_path: Path) -> None:
    """Verify that postmanify plan runs on backend fixture works as
    expected.

    Args:
        monkeypatch: Primary monkeypatch used by this step.
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo = _fixture_root("backend_service")
    monkeypatch.setattr(postmanify_cli, "repo_root", lambda: repo)
    env = tmp_path / "postmanify.envelope.json"
    code = postmanify_cli.main(["plan", "--envelope-out", str(env)])
    assert code == 0
    assert env.is_file()
    payload = json.loads(env.read_text(encoding="utf-8"))
    assert payload["suite"] == "postmanify"
