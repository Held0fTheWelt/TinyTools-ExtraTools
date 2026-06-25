"""Tests for final product cli.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.ai_suite_cli import main as suite_main
from fy_platform.tools.cli import main
from fy_platform.ai.workspace import workspace_root


def test_suite_catalog_and_command_reference(tmp_path: Path, capsys) -> None:
    """Verify that suite catalog and command reference works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = workspace_root(Path(__file__))
    code = main(['suite-catalog', '--project-root', str(workspace)])
    assert code == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_suite_catalog_and_command_reference.
    payload = json.loads(capsys.readouterr().out)
    names = {row['suite'] for row in payload['suites']}
    assert 'securify' in names
    assert 'templatify' in names
    assert (workspace / 'docs' / 'platform' / 'SUITE_CATALOG.md').is_file()

    code2 = main(['command-reference', '--project-root', str(workspace)])
    assert code2 == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_suite_catalog_and_command_reference.
    payload2 = json.loads(capsys.readouterr().out)
    assert 'generic_lifecycle_commands' in payload2
    assert 'securify' in payload2['suite_native_commands']
    assert (workspace / 'docs' / 'platform' / 'SUITE_COMMAND_REFERENCE.md').is_file()


def test_export_schemas_and_doctor_and_final_release_bundle(tmp_path: Path, capsys) -> None:
    """Verify that export schemas and doctor and final release bundle works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    workspace = workspace_root(Path(__file__))
    assert suite_main(['contractify', 'audit', '--target-repo', str(repo)]) == 0
    _ = capsys.readouterr().out

    code = main(['export-schemas', '--project-root', str(workspace)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['schema_count'] >= 5
    assert (workspace / 'docs' / 'platform' / 'schemas' / 'command_envelope.schema.json').is_file()

    doctor_code = main(['doctor', '--project-root', str(workspace)])
    assert doctor_code in {0, 5}
    doctor_payload = json.loads(capsys.readouterr().out)
    assert 'top_next_steps' in doctor_payload
    assert (workspace / 'docs' / 'platform' / 'DOCTOR.md').is_file()

    bundle_code = main(['final-release-bundle', '--project-root', str(workspace)])
    assert bundle_code in {0, 6}
    bundle_payload = json.loads(capsys.readouterr().out)
    assert bundle_payload['catalog']['suite_count'] >= 1
    assert bundle_payload['schemas']['schema_count'] >= 5
    assert (workspace / 'docs' / 'platform' / 'FINAL_RELEASE_BUNDLE.md').is_file()
