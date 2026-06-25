"""Follow-on blocker reduction tests for current fy-suites layouts."""
from __future__ import annotations

from pathlib import Path

from contractify.tools.drift_analysis import drift_docify_contractify_scan_root
from contractify.tools.runtime_mvp_spine import build_runtime_mvp_spine


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_docify_root_drift_is_not_reported_for_direct_repo_layout(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='fy-suites'\nversion='0.1.0'\n")
    _write(tmp_path / "fy_governance_enforcement.yaml", "ok: true\n")
    _write(
        tmp_path / "docify" / "tools" / "python_documentation_audit.py",
        "DEFAULT_RELATIVE_ROOTS = ('backend', \"'fy'-suites/contractify\")\n",
    )
    _write(tmp_path / "docify" / "README.md", "# Docify\n")

    findings = drift_docify_contractify_scan_root(tmp_path)

    assert findings == []


def test_runtime_spine_skips_manual_conflicts_without_current_repo_evidence(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='fy-suites'\nversion='0.1.0'\n")
    _write(tmp_path / "fy_governance_enforcement.yaml", "ok: true\n")
    _write(
        tmp_path / "docs" / "ADR" / "adr-0002-backend-session-surface-quarantine.md",
        "# ADR-0002\n\nStatus: Accepted\n",
    )

    _contracts, _projections, _relations, unresolved, _families = build_runtime_mvp_spine(
        tmp_path
    )

    assert unresolved == []
