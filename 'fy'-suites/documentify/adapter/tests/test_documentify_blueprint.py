"""Tests for documentify blueprint.

"""
from __future__ import annotations

from pathlib import Path

from documentify.tools.track_engine import generate_track_bundle


def test_documentify_generates_status_and_blueprint(tmp_path: Path) -> None:
    """Verify that documentify generates status and blueprint works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    (tmp_path / 'docs').mkdir()
    (tmp_path / '.github' / 'workflows').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / '.github' / 'workflows' / 'ci.yml').write_text('name: ci', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('root', encoding='utf-8')
    # Build filesystem locations and shared state that the rest of
    # test_documentify_generates_status_and_blueprint reuses.
    out_dir = tmp_path / 'generated'
    manifest = generate_track_bundle(tmp_path, out_dir, maturity='cross-linked')
    assert 'status' in manifest['tracks']
    assert (out_dir / 'technical' / 'DOCS_SITE_BLUEPRINT.md').is_file()
    assert (out_dir / 'status' / 'MOST_RECENT_NEXT_STEPS.md').is_file()
