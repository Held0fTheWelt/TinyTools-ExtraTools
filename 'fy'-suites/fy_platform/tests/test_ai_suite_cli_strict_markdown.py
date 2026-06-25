"""Tests for ai suite cli strict markdown.

"""
from fy_platform.tools.ai_suite_cli import main
from fy_platform.tests.fixtures_autark import create_target_repo


def test_ai_suite_cli_markdown_and_strict(tmp_path, monkeypatch, capsys):
    """Verify that ai suite cli markdown and strict works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    rc = main(['documentify', 'audit', '--target-repo', str(repo), '--format', 'markdown'])
    assert rc == 0
    out = capsys.readouterr().out
    assert '# documentify::audit' in out.lower()
    assert '- exit_code: `0`' in out.lower()

    rc2 = main(['contractify', 'init', '--target-repo', str(repo / 'missing'), '--strict'])
    assert rc2 == 1
