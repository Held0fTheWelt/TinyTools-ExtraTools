"""Tests for ai suite cli.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.ai_suite_cli import main


def test_generic_ai_suite_cli_docify_and_contractify_consolidate(tmp_path, monkeypatch, capsys):
    """Verify that generic ai suite cli docify and contractify consolidate
    works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    rc = main(['docify', 'audit', '--target-repo', str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out.lower()
    assert '"payload"' in out.lower()

    rc2 = main(['contractify', 'consolidate', '--target-repo', str(repo), '--apply-safe'])
    assert rc2 == 0
    out2 = capsys.readouterr().out
    assert 'contractify' in out2.lower()
    assert '"exit_code": 0' in out2.lower()
