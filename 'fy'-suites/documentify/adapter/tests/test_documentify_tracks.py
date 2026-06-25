"""Tests for documentify tracks.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from documentify.adapter.service import DocumentifyAdapter
from pathlib import Path
import json


def test_documentify_generates_track_manifest_and_ai_bundle(tmp_path, monkeypatch):
    """Verify that documentify generates track manifest and ai bundle works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    adapter = DocumentifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    # Build filesystem locations and shared state that the rest of
    # test_documentify_generates_track_manifest_and_ai_bundle reuses.
    generated_dir = Path(audit['generated_dir'])
    manifest = json.loads((generated_dir / 'document_manifest.json').read_text(encoding='utf-8'))
    assert 'ai-read' in manifest['tracks']
    assert (generated_dir / 'ai-read' / 'bundle.json').is_file()
    assert (generated_dir / 'INDEX.md').is_file()
