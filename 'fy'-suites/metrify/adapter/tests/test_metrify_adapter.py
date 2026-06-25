"""Tests for metrify adapter.

"""
from __future__ import annotations

from pathlib import Path

from metrify.adapter.service import MetrifyAdapter


def _workspace(tmp_path: Path) -> Path:
    """Workspace the requested operation.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    root = tmp_path / 'ws'
    root.mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'README.md').write_text('workspace\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'pyproject.toml').write_text('[project]\nname = "demo"\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'requirements.txt').write_text('\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'requirements-dev.txt').write_text('\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'requirements-test.txt').write_text('\n', encoding='utf-8')
    (root / 'fy_platform').mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'fy_governance_enforcement.yaml').write_text('ok: true\n', encoding='utf-8')
    suite = root / 'metrify'
    (suite / 'adapter').mkdir(parents=True)
    (suite / 'tools').mkdir(parents=True)
    (suite / 'reports').mkdir(parents=True)
    (suite / 'state').mkdir(parents=True)
    (suite / 'templates').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'README.md').write_text('metrify\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'adapter' / 'service.py').write_text('# stub\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'adapter' / 'cli.py').write_text('# stub\n', encoding='utf-8')
    return root


def test_adapter_audit_runs(tmp_path: Path) -> None:
    """Verify that adapter audit runs works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    root = _workspace(tmp_path)
    target = root / 'target'
    target.mkdir()
    adapter = MetrifyAdapter(root)
    result = adapter.audit(str(target))
    assert result['ok'] is True
    assert 'json_path' in result
