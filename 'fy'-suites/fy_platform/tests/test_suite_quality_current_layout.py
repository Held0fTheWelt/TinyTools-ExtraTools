"""Tests for suite quality current layout.

"""
from pathlib import Path

from fy_platform.ai.policy.suite_quality_policy import evaluate_suite_quality


def test_mature_optional_tests_paths_count_for_recent_suites(tmp_path: Path) -> None:
    """Verify that mature optional tests paths count for recent suites
    works as expected.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    root = tmp_path
    # Process name one item at a time so
    # test_mature_optional_tests_paths_count_for_recent_suites applies the same rule
    # across the full collection.
    for name in ['securify', 'usabilify', 'observifyfy']:
        suite = root / name
        (suite / 'adapter').mkdir(parents=True)
        (suite / 'tools' / 'tests').mkdir(parents=True)
        (suite / 'reports').mkdir(parents=True)
        (suite / 'state').mkdir(parents=True)
        (suite / 'templates').mkdir(parents=True)
        (suite / 'docs').mkdir(parents=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (suite / 'README.md').write_text('# ok\n', encoding='utf-8')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (suite / '__init__.py').write_text('', encoding='utf-8')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (suite / 'adapter' / 'service.py').write_text('', encoding='utf-8')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (suite / 'adapter' / 'cli.py').write_text('', encoding='utf-8')
    # Process name one item at a time so
    # test_mature_optional_tests_paths_count_for_recent_suites applies the same rule
    # across the full collection.
    for name in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt', 'README.md', 'pyproject.toml']:
        (root / name).write_text('', encoding='utf-8')
    result = evaluate_suite_quality(root, 'securify')
    assert 'missing_optional:tests' not in result['warnings']
