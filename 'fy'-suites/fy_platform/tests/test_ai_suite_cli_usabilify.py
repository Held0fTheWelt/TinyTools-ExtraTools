"""Tests for ai suite cli usabilify.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.ai_suite_cli import main


def test_generic_ai_suite_cli_usabilify_audit(tmp_path, monkeypatch, capsys):
    """Verify that generic ai suite cli usabilify audit works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    rc = main(['usabilify', 'audit', '--target-repo', str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'usabilify' in out.lower()
