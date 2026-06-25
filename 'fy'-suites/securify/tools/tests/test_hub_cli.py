"""Tests for hub cli.

"""
from fy_platform.tests.fixtures_autark import create_target_repo
from securify.tools.hub_cli import main


def test_securify_hub_cli_audit_json(tmp_path, capsys):
    """Verify that securify hub cli audit json works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    code = main(['audit', '--target-repo', str(repo), '--json'])
    assert code == 0
    out = capsys.readouterr().out
    assert 'security_ok' in out
