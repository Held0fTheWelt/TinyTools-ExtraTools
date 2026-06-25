from __future__ import annotations

import json
from pathlib import Path

from documentify.tools.track_engine import generate_track_bundle


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_generate_track_bundle_still_writes_manifest_and_index(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# Repo\n")
    _write(tmp_path / "pyproject.toml", "[project]\nname='repo'\nversion='0.1.0'\n")
    _write(tmp_path / "fy_governance_enforcement.yaml", "ok: true\n")
    _write(tmp_path / "docs" / "technical" / "ai" / "RAG.md", "# RAG\n")
    out = tmp_path / "documentify" / "generated" / "repo" / "bundle"
    manifest = generate_track_bundle(tmp_path, out)
    assert manifest["generated_count"] >= 3
    data = json.loads((out / "document_manifest.json").read_text(encoding="utf-8"))
    assert data["template_engine"] in {"builtin-fallback", "templatify"}
    assert (out / "INDEX.md").is_file()
