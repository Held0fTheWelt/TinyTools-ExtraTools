"""Tests for hub cli.

"""
from __future__ import annotations

import json
from pathlib import Path

from metrify.tools.hub_cli import main


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
    return root


def test_cli_record_and_report(tmp_path: Path, monkeypatch) -> None:
    """Verify that cli record and report works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    root = _workspace(tmp_path)
    monkeypatch.setenv('METRIFY_REPO_ROOT', str(root))
    assert main(['record', '--suite', 'contractify', '--run-id', 'r1', '--model', 'gpt-5.4-mini', '--timestamp-utc', '2026-04-18T00:00:00+00:00', '--input-tokens', '1000', '--output-tokens', '1000', '--quiet']) == 0
    assert main(['report', '--quiet']) == 0
    payload = json.loads((root / 'metrify' / 'reports' / 'metrify_cost_report.json').read_text(encoding='utf-8'))
    assert payload['event_count'] == 1
