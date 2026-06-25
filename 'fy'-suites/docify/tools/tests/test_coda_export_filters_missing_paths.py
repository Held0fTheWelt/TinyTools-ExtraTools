"""Docify Coda export filtering tests."""
from __future__ import annotations

import json
from pathlib import Path

from docify.tools.coda_exports import build_docify_obligation_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_docify_export_drops_missing_repo_paths(tmp_path: Path) -> None:
    (tmp_path / "docify").mkdir(parents=True, exist_ok=True)
    _write_json(
        tmp_path / "docify" / "baseline_docstring_coverage.json",
        {
            "findings": [
                {"path": "missing/module.py", "name": "ghost"},
                {"path": "real/module.py", "name": "keep_me"},
            ],
            "parse_errors": [
                "missing/module.py: SyntaxError: boom",
                "real/module.py: SyntaxError: boom",
            ],
        },
    )
    real_module = tmp_path / "real" / "module.py"
    real_module.parent.mkdir(parents=True, exist_ok=True)
    real_module.write_text("def keep_me():\n    return 1\n", encoding="utf-8")

    manifest = build_docify_obligation_manifest(tmp_path)

    assert [item["path"] for item in manifest["required_docs"]] == [
        "real/module.py",
    ]
    assert [item["obligation_id"] for item in manifest["obligations"]] == [
        "docify:real/module.py:keep_me"
    ]
