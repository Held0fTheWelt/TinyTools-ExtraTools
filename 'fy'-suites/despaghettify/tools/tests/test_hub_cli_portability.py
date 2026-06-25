"""Tests for hub cli portability.

"""
from __future__ import annotations

import json
from pathlib import Path

from despaghettify.tools import hub_cli


def test_check_runs_with_manifest_driven_non_wos_root(monkeypatch, tmp_path: Path) -> None:
    """Verify that check runs with manifest driven non wos root works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        monkeypatch: Primary monkeypatch used by this step.
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    repo = tmp_path / "portable-repo"
    src = repo / "src"
    src.mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (repo / "fy-manifest.yaml").write_text(
        "manifestVersion: 1\n"
        "suites:\n"
        "  despaghettify:\n"
        "    scan_roots:\n"
        "      - src\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESPAG_REPO_ROOT", str(repo))
    out = repo / "despag-check.json"
    code = hub_cli.main(["check", "--out", str(out)])
    assert code == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_check_runs_with_manifest_driven_non_wos_root.
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["kind"] == "despaghettify_check"
    assert payload["ds005"]["enabled"] is False
