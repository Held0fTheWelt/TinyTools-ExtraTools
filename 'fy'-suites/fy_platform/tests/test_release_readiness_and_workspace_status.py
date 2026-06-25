"""Tests for release readiness and workspace status.

"""
from __future__ import annotations

from pathlib import Path

from contractify.adapter.service import ContractifyAdapter
from documentify.adapter.service import DocumentifyAdapter
from fy_platform.ai.release_readiness import suite_release_readiness, workspace_release_readiness, write_workspace_release_site
from fy_platform.ai.workspace_status_site import build_workspace_status_site, write_workspace_status_site
from fy_platform.tests.fixtures_autark import create_target_repo


def test_suite_release_readiness_after_successful_runs(tmp_path, monkeypatch):
    """Verify that suite release readiness after successful runs works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    c = ContractifyAdapter()
    d = DocumentifyAdapter()
    c.audit(str(repo))
    d.audit(str(repo))
    # Assemble the structured result data before later steps enrich or return it from
    # test_suite_release_readiness_after_successful_runs.
    payload = suite_release_readiness(c.root, 'contractify')
    assert payload['ready'] is True
    assert payload['latest_run'] is not None
    assert payload['status_page_md'] is not None


def test_workspace_status_site_and_release_site_are_written(tmp_path, monkeypatch):
    """Verify that workspace status site and release site are written works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        monkeypatch: Primary monkeypatch used by this step.
    """
    repo = create_target_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    c = ContractifyAdapter()
    c.audit(str(repo))
    status_payload = build_workspace_status_site(c.root, ['contractify', 'documentify'])
    status_paths = write_workspace_status_site(c.root, status_payload)
    assert (c.root / status_paths['workspace_status_site_md_path']).is_file()
    release_payload = workspace_release_readiness(c.root, ['contractify', 'documentify'])
    release_paths = write_workspace_release_site(c.root, release_payload)
    assert (c.root / release_paths['workspace_status_md_path']).is_file()
    assert 'contractify' in [row['suite'] for row in status_payload['suites']]
