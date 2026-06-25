"""Tests for Markdown-backed strategy profiles."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fy_platform.ai.strategy_profiles import load_active_strategy_profile, strategy_file_path, validate_profile
from fy_platform.tools.cli import main



def _mk_workspace(tmp_path: Path) -> Path:
    (tmp_path / 'README.md').write_text('# test\n', encoding='utf-8')
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n', encoding='utf-8')
    (tmp_path / 'fy_governance_enforcement.yaml').write_text('mode: test\n', encoding='utf-8')
    for name in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
        (tmp_path / name).write_text('\n', encoding='utf-8')
    return tmp_path



def test_strategy_file_is_discoverable_parseable_and_defaults_to_d(tmp_path: Path, capsys) -> None:
    ws = _mk_workspace(tmp_path)
    code = main(['strategy', 'show', '--project-root', str(ws)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['active_profile'] == 'D'
    path = strategy_file_path(ws)
    assert path.is_file()
    profile = load_active_strategy_profile(ws)
    assert profile.active_profile == 'D'
    assert profile.source_path == 'FY_STRATEGY_SETTINGS.md'



def test_strategy_set_persists_expected_state(tmp_path: Path, capsys) -> None:
    ws = _mk_workspace(tmp_path)
    code = main(['strategy', 'set', 'B', '--project-root', str(ws)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['active_profile'] == 'B'
    assert 'profile_label' in payload
    assert 'active_profile: B' in (ws / 'FY_STRATEGY_SETTINGS.md').read_text(encoding='utf-8')
    mirror = ws / 'fy_platform' / 'state' / 'strategy_profiles' / 'FY_ACTIVE_STRATEGY.md'
    assert mirror.is_file()
    assert 'active_profile: B' in mirror.read_text(encoding='utf-8')



def test_invalid_profiles_are_rejected() -> None:
    with pytest.raises(ValueError):
        validate_profile('Z')
