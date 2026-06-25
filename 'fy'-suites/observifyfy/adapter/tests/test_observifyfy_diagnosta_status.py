"""Tests for observifyfy visibility of Diagnosta readiness signals."""
from __future__ import annotations

from pathlib import Path

from diagnosta.adapter.service import DiagnostaAdapter
from observifyfy.adapter.service import ObservifyfyAdapter


def _mk_workspace(tmp_path: Path) -> Path:
    for name, text in {
        "README.md": "# test\n",
        "pyproject.toml": '[project]\nname="x"\nversion="0"\n',
        "fy_governance_enforcement.yaml": "mode: test\n",
        "requirements.txt": "\n",
        "requirements-dev.txt": "\n",
        "requirements-test.txt": "\n",
    }.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    for suite in ["diagnosta", "observifyfy"]:
        for rel in ["adapter", "tools", "reports", "state", "templates"]:
            (tmp_path / suite / rel).mkdir(parents=True, exist_ok=True)
        (tmp_path / suite / "README.md").write_text(
            f"# {suite}\n", encoding="utf-8"
        )
        (tmp_path / suite / "adapter" / "service.py").write_text(
            "class Placeholder: pass\n", encoding="utf-8"
        )
        (tmp_path / suite / "adapter" / "cli.py").write_text(
            "def main():\n    return 0\n", encoding="utf-8"
        )
    return tmp_path


def test_observifyfy_audit_surfaces_active_profile_and_diagnosta_artifacts(
    tmp_path: Path,
) -> None:
    ws = _mk_workspace(tmp_path)
    diagnosta = DiagnostaAdapter(root=ws)
    diagnosta.audit(str(ws))
    observifyfy = ObservifyfyAdapter(root=ws)
    payload = observifyfy.audit(str(ws))
    assert payload["ok"] is True
    assert payload["active_strategy_profile"]["active_profile"] == "D"
    assert payload["diagnosta_signal"]["present"] is True
    assert payload["diagnosta_signal"]["readiness_case"]["readiness_status"]
    assert (ws / "observifyfy" / "reports" / "observifyfy_diagnosta_signal.json").is_file()
