"""Tests for observifyfy integration.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.final_product import suite_catalog_payload
from fy_platform.ai.workspace import ensure_workspace_layout
from fy_platform.ai.workspace_status_site import build_workspace_status_site, write_workspace_status_site


def _mk_workspace(tmp_path: Path) -> Path:
    """Mk workspace.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / "pyproject.toml").write_text("[project]\nname=\"x\"\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / "fy_governance_enforcement.yaml").write_text("ok: true\n", encoding="utf-8")
    ensure_workspace_layout(tmp_path)
    # Process suite one item at a time so _mk_workspace applies the same rule across the
    # full collection.
    for suite in ["contractify", "observifyfy"]:
        root = tmp_path / suite
        # Process rel one item at a time so _mk_workspace applies the same rule across
        # the full collection.
        for rel in ["adapter", "tools", "reports/status", "state", "templates"]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (root / "README.md").write_text(f"# {suite}\n", encoding="utf-8")
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (root / "adapter" / "service.py").write_text("class X: pass\n", encoding="utf-8")
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (root / "adapter" / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        status = {"ok": True, "summary": "ok", "next_steps": ["continue"], "command": "audit", "latest_run": {"run_id": "r1"}}
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (root / "reports" / "status" / "most_recent_next_steps.json").write_text(json.dumps(status), encoding="utf-8")
    return tmp_path


def test_suite_catalog_includes_observifyfy(tmp_path: Path) -> None:
    """Verify that suite catalog includes observifyfy works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    ws = _mk_workspace(tmp_path)
    payload = suite_catalog_payload(ws)
    suites = {row["suite"] for row in payload["suites"]}
    assert "observifyfy" in suites


def test_workspace_status_site_writes_internal_mirror(tmp_path: Path) -> None:
    """Verify that workspace status site writes internal mirror works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    ws = _mk_workspace(tmp_path)
    payload = build_workspace_status_site(ws)
    paths = write_workspace_status_site(ws, payload)
    assert (ws / 'docs' / 'platform' / 'workspace_status_site.json').is_file()
    assert (ws / 'docs' / 'platform' / 'WORKSPACE_STATUS_SITE.md').is_file()
    assert paths["workspace_status_site_internal_json_path"] == "docs/platform/workspace_status_site.json"
