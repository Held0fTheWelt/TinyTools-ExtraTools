"""Tests for manifest first profile.

"""
from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stderr
from pathlib import Path

import contractify.tools.repo_paths as repo_paths
from contractify.tools.hub_cli import main as contractify_main
from fy_platform.core.manifest import load_manifest, suite_config
from fy_platform.tools.cli import main as fy_main


def _tmp_report(root: Path, stem: str) -> Path:
    """Tmp report.

    Args:
        root: Root directory used to resolve repository-local paths.
        stem: Primary stem used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return root / "'fy'-suites" / "contractify" / "reports" / stem


def _tracked_snapshot(root: Path) -> Path:
    """Tracked snapshot.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return root / "'fy'-suites" / "contractify" / "reports" / "CANONICAL_REPO_ROOT_AUDIT.md"


def _extract_count(body: str, label: str) -> int:
    """Extract count.

    Args:
        body: Primary body used by this step.
        label: Primary label used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    match = re.search(rf"{re.escape(label)}: \*\*(\d+)\*\*", body)
    assert match, f"missing markdown count for {label}"
    return int(match.group(1))


def test_repo_root_manifest_exists_and_validates(capsys) -> None:
    """Verify that repo root manifest exists and validates works as
    expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    root = repo_paths.repo_root()
    manifest, warnings = load_manifest(root)
    assert manifest is not None
    assert warnings == []
    cfg = suite_config(manifest, "contractify")
    assert cfg.get("openapi") == "docs/api/openapi.yaml"
    assert cfg.get("max_contracts") == 60
    assert cfg.get("canonical_audit_snapshot_md") == "'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md"

    code = fy_main(["validate-manifest", "--project-root", str(root)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_canonical_audit_cli_uses_manifest_profile_without_fallback() -> None:
    """Verify that canonical audit cli uses manifest profile without
    fallback works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = repo_paths.repo_root()
    out = _tmp_report(root, "_pytest_manifest_first_audit.json")
    out_arg = out.relative_to(root).as_posix()
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            code = contractify_main(["audit", "--out", out_arg, "--quiet"])
        assert code == 0
        assert "legacy fallback" not in stderr.getvalue().lower()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["execution_profile"]["max_contracts"] == 60
        ids = {c["id"] for c in payload["contracts"]}
        assert "CTR-RUNTIME-AUTHORITY-STATE-FLOW" in ids
        assert "CTR-RAG-GOVERNANCE" in ids
    finally:
        if out.is_file():
            out.unlink()


def test_canonical_markdown_snapshot_matches_fresh_canonical_run() -> None:
    """Verify that canonical markdown snapshot matches fresh canonical run
    works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = repo_paths.repo_root()
    tracked = _tracked_snapshot(root)
    assert tracked.is_file()
    fresh = _tmp_report(root, "_pytest_manifest_first_fresh_audit.json")
    fresh_arg = fresh.relative_to(root).as_posix()
    try:
        code = contractify_main(["audit", "--out", fresh_arg, "--quiet"])
        assert code == 0
        fresh_payload = json.loads(fresh.read_text(encoding="utf-8"))
        body = tracked.read_text(encoding="utf-8")
        assert _extract_count(body, "Contractify max contracts") == fresh_payload["execution_profile"]["max_contracts"]
        assert _extract_count(body, "Contracts discovered in audit") == fresh_payload["stats"]["n_contracts"]
        assert _extract_count(body, "Projections discovered in audit") == fresh_payload["stats"]["n_projections"]
        assert _extract_count(body, "Relations discovered in audit") == fresh_payload["stats"]["n_relations"]
        assert _extract_count(body, "Drift findings in audit") == fresh_payload["stats"]["n_drifts"]
        assert _extract_count(body, "Conflicts in audit") == fresh_payload["stats"]["n_conflicts"]
        assert _extract_count(body, "Manual unresolved areas kept explicit") == fresh_payload["stats"]["n_manual_unresolved_areas"]
        assert "Tracked canonical review evidence is markdown" in body
        assert "_local_contract_audit.json" in body
    finally:
        if fresh.is_file():
            fresh.unlink()


def test_runtime_mvp_report_mentions_tracked_markdown_snapshot_and_canonical_stats() -> None:
    """Verify that runtime mvp report mentions tracked markdown snapshot
    and canonical stats works as expected.
    """
    root = repo_paths.repo_root()
    snapshot = _tracked_snapshot(root)
    report = root / "'fy'-suites" / "contractify" / "reports" / "runtime_mvp_attachment_report.md"
    body = report.read_text(encoding="utf-8")
    snapshot_body = snapshot.read_text(encoding="utf-8")
    contracts = _extract_count(snapshot_body, "Contracts discovered in audit")
    relations = _extract_count(snapshot_body, "Relations discovered in audit")
    unresolved = _extract_count(snapshot_body, "Manual unresolved areas kept explicit")
    assert "Canonical tracked audit snapshot" in body
    assert "CANONICAL_REPO_ROOT_AUDIT.md" in body
    assert f"Contracts discovered in audit: **{contracts}**" in body
    assert f"Relations discovered in audit: **{relations}**" in body
    assert f"Manual unresolved areas kept explicit: **{unresolved}**" in body


def test_reports_policy_is_markdown_tracked_json_ephemeral() -> None:
    """Verify that reports policy is markdown tracked json ephemeral works
    as expected.
    """
    root = repo_paths.repo_root()
    reports_readme = (root / "'fy'-suites" / "contractify" / "reports" / "README.md").read_text(encoding="utf-8")
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert "tracked human-readable markdown" in reports_readme
    assert "intentionally ephemeral" in reports_readme
    assert "**/contractify/reports/*.json" in gitignore


def test_helper_paths_use_markdown_policy_and_local_json_names() -> None:
    """Verify that helper paths use markdown policy and local json names
    works as expected.
    """
    root = repo_paths.repo_root()
    helper = (root / ".scripts" / "regenerate_contract_audit.py").read_text(encoding="utf-8")
    skill = (root / ".cursor" / "skills" / "contractify-check" / "SKILL.md").read_text(encoding="utf-8")
    changed = (root / "CHANGED_FILES.txt").read_text(encoding="utf-8")
    assert "_local_contract_audit.json" in helper
    assert "CANONICAL_REPO_ROOT_AUDIT.md" in helper
    assert "runtime_mvp_attachment_report.md" in helper
    assert "reports/contract_audit.json" not in skill
    assert "reports/contract_audit.json" not in changed
    assert "reports/contract_discovery.json" not in changed
