"""Tests for hub cli.

"""
from __future__ import annotations

from pathlib import Path

from docify.tools.hub_cli import main, parse_open_doc_ids


def test_parse_open_doc_ids_sorts_and_dedupes() -> None:
    """Verify that parse open doc ids sorts and dedupes works as expected.
    """
    md = """
## Backlog
| **DOC-002** | a |
| **DOC-001** | b |
| **DOC-002** | dup |
"""
    assert parse_open_doc_ids(md) == ["DOC-001", "DOC-002"]


def test_open_doc_cli_with_explicit_input(tmp_path: Path, capsys) -> None:
    """CLI must not require monorepo pyproject when --input points at a
    backlog file.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    p = tmp_path / "documentation_implementation_input.md"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    p.write_text(
        "| **DOC-001** | cat | slice | OPEN | note |\n",
        encoding="utf-8",
    )
    code = main(["open-doc", "--input", str(p)])
    assert code == 0
    assert capsys.readouterr().out.strip() == "DOC-001"


def test_inline_explain_command_smoke(tmp_path: Path, capsys) -> None:
    """Verify that inline explain command smoke works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    src = tmp_path / 'sample.py'
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    src.write_text(
        'def helper():\n    json_path = run_dir / \"out.json\"\n    write_json(json_path, payload)\n',
        encoding='utf-8',
    )
    code = main(['inline-explain', '--file', str(src), '--function', 'helper'])
    assert code == 0
    out = capsys.readouterr().out
    assert 'Build filesystem locations' in out
    assert 'Persist the structured JSON representation' in out


def test_open_doc_monorepo_default_uses_repo_when_available(tmp_path: Path, monkeypatch, capsys) -> None:
    """When --input is omitted, behaviour still depends on repo_root (smoke
    only in-layout).

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
        capsys: Primary capsys used by this step.
    """
    from docify.tools import hub_cli as hc

    root = tmp_path / "repo"
    root.mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "pyproject.toml").write_text('name = "world-of-shadows-hub"\n', encoding="utf-8")
    suites = root / "'fy'-suites"
    hub = suites / "docify"
    hub.mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (hub / "documentation_implementation_input.md").write_text(
        "| **DOC-042** | x | y | OPEN | z |\n",
        encoding="utf-8",
    )

    def fake_root() -> Path:
        """Fake root.

        Returns:
            Path:
                Filesystem path produced or resolved by
                this callable.
        """
        return root.resolve()

    monkeypatch.setattr(hc, "repo_root", fake_root)
    code = hc.main(["open-doc"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "DOC-042"
