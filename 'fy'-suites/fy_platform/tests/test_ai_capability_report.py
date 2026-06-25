"""Tests for ai capability report.

"""
from __future__ import annotations

from fy_platform.ai.final_product import ai_capability_payload, suite_catalog_payload


def test_ai_capability_payload_includes_mvpify(tmp_path):
    """Verify that ai capability payload includes mvpify works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_ai_capability_payload_includes_mvpify.
    payload = ai_capability_payload(tmp_path)
    assert payload['schema_version'] == 'fy.ai-capability.v1'
    assert 'mvpify' in payload['per_suite']
    assert 'prepared MVP import' in ' '.join(payload['per_suite']['mvpify'])


def test_suite_catalog_can_include_mvpify(tmp_path):
    """Verify that suite catalog can include mvpify works as expected.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'fy_governance_enforcement.yaml').write_text('mode: test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('# test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n', encoding='utf-8')
    for req in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
        (tmp_path / req).write_text('\n', encoding='utf-8')
    (tmp_path / 'mvpify' / 'adapter').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'mvpify' / 'adapter' / 'service.py').write_text('', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'mvpify' / 'README.md').write_text('# mvpify\n', encoding='utf-8')
    (tmp_path / 'mvpify' / 'reports').mkdir(parents=True)
    (tmp_path / 'mvpify' / 'state').mkdir(parents=True)
    (tmp_path / 'mvpify' / 'tools').mkdir(parents=True)
    (tmp_path / 'mvpify' / 'templates').mkdir(parents=True)
    payload = suite_catalog_payload(tmp_path)
    assert any(row['suite'] == 'mvpify' for row in payload['suites'])
