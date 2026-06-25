"""Tests for python documentation audit.

"""
from __future__ import annotations

from pathlib import Path

import json

from docify.tools.python_documentation_audit import audit_file, main


def test_audit_file_flags_missing_module_docstring(tmp_path: Path) -> None:
    """Verify that audit file flags missing module docstring works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    path = tmp_path / "sample.py"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text("def public() -> int:\n    return 1\n", encoding="utf-8")
    # Assemble the structured result data before later steps enrich or return it from
    # test_audit_file_flags_missing_module_docstring.
    findings = audit_file(path, rel_path="sample.py", include_private=False)
    kinds = {f.kind for f in findings}
    assert "module" in kinds
    assert "function" in kinds


def test_audit_skips_visit_methods_on_private_visitor(tmp_path: Path) -> None:
    """Verify that audit skips visit methods on private visitor works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    path = tmp_path / "visitor.py"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(
        "import ast\n\n"
        "class _V(ast.NodeVisitor):\n"
        "    def visit_Name(self, node: ast.Name) -> None:\n"
        "        return None\n",
        encoding="utf-8",
    )
    findings = audit_file(path, rel_path="visitor.py", include_private=False)
    names = {f.name for f in findings}
    assert "visit_Name" not in names


def test_json_mode_can_emit_shared_envelope(tmp_path: Path) -> None:
    """Verify that json mode can emit shared envelope works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    src = tmp_path / "pkg"
    src.mkdir()
    py_file = src / "sample.py"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    py_file.write_text("def f():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "audit.json"
    env = tmp_path / "audit.envelope.json"
    code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--root",
            "pkg",
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
    payload = json.loads(env.read_text(encoding="utf-8"))
    assert payload["envelopeVersion"] == "1"
    assert isinstance(payload["findings"], list)
    assert payload["deprecations"]
    dep_md = env.with_suffix(env.suffix + ".deprecations.md")
    assert dep_md.is_file()
