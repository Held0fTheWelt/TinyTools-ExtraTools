"""Tests for ai suite cli exception envelope.

"""
from __future__ import annotations

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.tools import ai_suite_cli


class BrokenAdapter(BaseSuiteAdapter):
    """Adapter implementation for broken workflows.
    """
    def __init__(self, root=None):
        """Initialize BrokenAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('brokenify', root)

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        raise RuntimeError('boom')


def test_ai_suite_cli_wraps_command_exceptions(tmp_path, monkeypatch, capsys):
    """Verify that ai suite cli wraps command exceptions works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
        capsys: Primary capsys used by this step.
    """
    monkeypatch.chdir(tmp_path)
    original = dict(ai_suite_cli.SUITES)
    ai_suite_cli.SUITES['brokenify'] = BrokenAdapter
    # Protect the critical test_ai_suite_cli_wraps_command_exceptions work so failures
    # can be turned into a controlled result or cleanup path.
    try:
        rc = ai_suite_cli.main(['brokenify', 'audit', '--target-repo', str(tmp_path)])
        assert rc == 5
        out = capsys.readouterr().out.lower()
        assert 'command_exception' in out
        assert 'recovery_hints' in out
    finally:
        ai_suite_cli.SUITES.clear()
        ai_suite_cli.SUITES.update(original)
