"""Tests for adapter.

"""
from __future__ import annotations

from pathlib import Path

from observifyfy.adapter.service import ObservifyfyAdapter


def test_observifyfy_adapter_init_and_audit(tmp_path: Path) -> None:
    """Verify that observifyfy adapter init and audit works as expected.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
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
    (tmp_path / ".fydata").mkdir()
    # Process name one item at a time so test_observifyfy_adapter_init_and_audit applies
    # the same rule across the full collection.
    for name in ["requirements.txt", "requirements-dev.txt", "requirements-test.txt"]:
        (tmp_path / name).write_text("# stub\n", encoding="utf-8")
    suite = tmp_path / "observifyfy"
    # Process rel one item at a time so test_observifyfy_adapter_init_and_audit applies
    # the same rule across the full collection.
    for rel in ["adapter", "tools", "reports", "state", "templates"]:
        (suite / rel).mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / "README.md").write_text("# observifyfy\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / "adapter" / "service.py").write_text("class Service: pass\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / "adapter" / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    # Assemble the structured result data before later steps enrich or return it from
    # test_observifyfy_adapter_init_and_audit.
    adapter = ObservifyfyAdapter(tmp_path)
    init_payload = adapter.init(str(tmp_path))
    assert init_payload["ok"] is True
    # Assemble the structured result data before later steps enrich or return it from
    # test_observifyfy_adapter_init_and_audit.
    audit_payload = adapter.audit(str(tmp_path))
    assert audit_payload["ok"] is True
