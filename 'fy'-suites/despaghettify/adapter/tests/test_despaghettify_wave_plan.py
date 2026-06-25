"""Tests for despaghettify wave plan.

"""
from pathlib import Path
import json

from fy_platform.tests.fixtures_autark import create_target_repo
from despaghettify.adapter.service import DespaghettifyAdapter


def test_despaghettify_generates_wave_plan(tmp_path, monkeypatch):
    """Verify that despaghettify generates wave plan works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    spike = repo / 'src' / 'spike.py'
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    spike.write_text('\n'.join(['x = 1'] * 420), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    adapter = DespaghettifyAdapter()
    audit = adapter.audit(str(repo))
    assert audit['ok'] is True
    # Assemble the structured result data before later steps enrich or return it from
    # test_despaghettify_generates_wave_plan.
    payload = json.loads(Path(audit['json_path']).read_text(encoding='utf-8'))
    assert payload['wave_plan']['action_count'] >= 1
    assert payload['global_category'] == 'low'
