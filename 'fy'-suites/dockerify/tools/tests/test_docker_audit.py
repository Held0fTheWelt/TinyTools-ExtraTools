"""Tests for docker audit.

"""
import json

from dockerify.tools.docker_audit import audit_docker_surface
from dockerify.tools.hub_cli import main
from dockerify.tools.repo_paths import repo_root


def test_audit_docker_surface_detects_services() -> None:
    """Verify that audit docker surface detects services works as expected.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # test_audit_docker_surface_detects_services.
    payload = audit_docker_surface(repo_root())
    assert payload['summary']['present_service_count'] == 4
    assert payload['summary']['migration_on_start'] is True
    assert payload['findings'] == []


def test_cli_writes_reports() -> None:
    """Verify that cli writes reports works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = repo_root()
    out = root / "'fy'-suites" / 'dockerify' / 'reports' / '_pytest_dockerify_audit.json'
    md = root / "'fy'-suites" / 'dockerify' / 'reports' / '_pytest_dockerify_audit.md'
    try:
        code = main(['audit', '--out', out.relative_to(root).as_posix(), '--md-out', md.relative_to(root).as_posix(), '--quiet'])
        assert code == 0
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['suite'] == 'dockerify'
        assert md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if md.is_file():
            md.unlink()
