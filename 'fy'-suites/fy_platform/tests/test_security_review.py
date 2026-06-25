"""Tests for security review.

"""
from __future__ import annotations

from fy_platform.ai.security_review import scan_workspace_security


def test_security_review_finds_tracked_env_file(tmp_path, monkeypatch):
    """Verify that security review finds tracked env file works as
    expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    monkeypatch.chdir(tmp_path)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('x', encoding='utf-8')
    (tmp_path / 'fy_platform').mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / '.env').write_text('OPENAI_API_KEY="secret"\n', encoding='utf-8')
    # Assemble the structured result data before later steps enrich or return it from
    # test_security_review_finds_tracked_env_file.
    payload = scan_workspace_security(tmp_path)
    assert payload['ok'] is False
    assert payload['risky_file_count'] >= 1 or payload['secret_hit_count'] >= 1
