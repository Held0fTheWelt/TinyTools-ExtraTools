from __future__ import annotations

import json
from pathlib import Path

from delagecy.tools.hub_cli import main
from delagecy.tools.scanner import scan


def test_scan_finds_ui_legacy_hit(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    target = root / "administration-tool" / "templates" / "manage"
    target.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "'fy'-suites").mkdir()
    (target / "page.html").write_text("<div>Legacy compatibility</div>\n", encoding="utf-8")

    payload = scan(root)

    assert payload["hit_count"] == 1
    hit = payload["hits"][0]
    assert hit["kind"] == "ui"
    assert hit["path"].endswith("page.html")


def test_cli_register_approve_and_mark_removed(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    src = root / "app.py"
    suite.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    src.write_text("# legacy path\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    assert main(["scan", "--out", str(scan_json)]) == 0
    payload = json.loads(scan_json.read_text(encoding="utf-8"))
    fp = payload["hits"][0]["fingerprint"]

    assert main(["register", "--scan-json", str(scan_json), "--fingerprint", fp, "--title", "legacy path"]) == 0
    assert main(["approve", "--id", "DLG-001", "--approved-by", "test", "--note", "approved"]) == 0
    assert main(["mark-removed", "--id", "DLG-001", "--verification", "verified"]) == 0

    out = capsys.readouterr().out
    assert "DLG-001" in out


def test_cli_mark_canonicalized_records_active_behavior_scope(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    src = root / "app.py"
    suite.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    src.write_text("# compatibility for alternate provider\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    assert main(["scan", "--out", str(scan_json)]) == 0
    payload = json.loads(scan_json.read_text(encoding="utf-8"))
    fp = payload["hits"][0]["fingerprint"]

    assert main(["register", "--scan-json", str(scan_json), "--fingerprint", fp, "--title", "provider variant"]) == 0
    assert main(
        [
            "mark-canonicalized",
            "--id",
            "DLG-001",
            "--compatibility-scope",
            "provider_or_adapter_variation",
            "--reason",
            "provider variant remains active",
            "--evidence",
            "test evidence",
        ]
    ) == 0

    registry = json.loads((suite / "delagecy_registry.json").read_text(encoding="utf-8"))
    row = registry["findings"][0]
    assert row["status"] == "canonicalized_active_behavior"
    assert row["canonicalization"]["compatibility_scope"] == "provider_or_adapter_variation"


def test_cli_mark_canonicalized_rejects_previous_version_scope(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    src = root / "app.py"
    suite.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    src.write_text("# legacy path\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    assert main(["scan", "--out", str(scan_json)]) == 0
    payload = json.loads(scan_json.read_text(encoding="utf-8"))
    fp = payload["hits"][0]["fingerprint"]

    assert main(["register", "--scan-json", str(scan_json), "--fingerprint", fp, "--title", "old version"]) == 0
    assert main(
        [
            "mark-canonicalized",
            "--id",
            "DLG-001",
            "--compatibility-scope",
            "previous_version",
            "--reason",
            "old clients",
            "--evidence",
            "none",
        ]
    ) == 2


def test_scanner_can_scan_delagecy_internal_selftest_area(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    internal = root / "'fy'-suites" / "delagecy" / "internal"
    internal.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (internal / "fixture.py").write_text("# legacy fixture\n", encoding="utf-8")

    payload = scan(root, include=["'fy'-suites/delagecy/internal"])

    assert payload["hit_count"] == 1
    assert payload["hits"][0]["path"].endswith("delagecy/internal/fixture.py")


def test_scanner_excludes_delagecy_reports_from_active_surface(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    reports = root / "'fy'-suites" / "delagecy" / "reports"
    reports.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (reports / "audit.md").write_text("# legacy evidence report\n", encoding="utf-8")

    payload = scan(root)

    assert payload["hit_count"] == 0


def test_report_command_writes_readable_markdown(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    template = root / "frontend" / "templates"
    suite.mkdir(parents=True)
    template.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (template / "play.html").write_text("<button>Legacy mode</button>\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    report_md = suite / "report.md"

    assert main(["scan", "--out", str(scan_json)]) == 0
    assert main(["report", "--scan-json", str(scan_json), "--out", str(report_md)]) == 0

    text = report_md.read_text(encoding="utf-8")
    assert "# Delagecy Legacy Scan Report" in text
    assert "Gate status: **FAIL**" in text
    assert "## First Unregistered Findings" in text
    assert "## UI Residue Examples" in text


def test_register_batch_can_approve_new_hits(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    suite = root / "'fy'-suites" / "delagecy"
    suite.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "one.py").write_text("# legacy one\n", encoding="utf-8")
    (root / "two.py").write_text("# legacy two\n", encoding="utf-8")
    monkeypatch.chdir(root)

    scan_json = suite / "scan.json"
    assert main(["scan", "--out", str(scan_json)]) == 0
    assert main(["register-batch", "--scan-json", str(scan_json), "--approve"]) == 0

    registry = json.loads((suite / "delagecy_registry.json").read_text(encoding="utf-8"))
    assert [row["status"] for row in registry["findings"]] == [
        "approved_for_removal",
        "approved_for_removal",
    ]
    assert '"registered_count": 2' in capsys.readouterr().out
