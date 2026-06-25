"""Tests for test governance.

"""
import json

import testify.tools.repo_paths as testify_repo_paths
from testify.tools.hub_cli import main
from testify.tools.test_governance import audit_test_governance


def test_audit_test_governance_detects_required_workflows() -> None:
    """Verify that audit test governance detects required workflows works
    as expected.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_audit_test_governance_detects_required_workflows.
    payload = audit_test_governance(testify_repo_paths.repo_root())
    assert payload['summary']['finding_count'] == 0
    assert 'dockerify' in payload['hub_pyproject']['scripts']
    assert 'backend' in payload['runner']['suite_targets']


def test_cli_writes_reports() -> None:
    """Verify that cli writes reports works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = testify_repo_paths.repo_root()
    out = root / "'fy'-suites" / 'testify' / 'reports' / '_pytest_testify_audit.json'
    md = root / "'fy'-suites" / 'testify' / 'reports' / '_pytest_testify_audit.md'
    try:
        code = main(['audit', '--out', out.relative_to(root).as_posix(), '--md-out', md.relative_to(root).as_posix(), '--quiet'])
        assert code == 0
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['suite'] == 'testify'
        assert md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if md.is_file():
            md.unlink()
