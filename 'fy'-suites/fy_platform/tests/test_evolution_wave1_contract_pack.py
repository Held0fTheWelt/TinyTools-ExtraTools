"""Tests for evolution wave1 contract pack.

"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from fy_platform.ai.evolution_contract_pack import canonical_schema_source_dir, suite_names_for_ownership
from fy_platform.ai.workspace import workspace_root
from fy_platform.tools.cli import main

EXPECTED_CANONICAL_SCHEMA_NAMES = {'fy_unit.schema.json','relation.schema.json','artifact.schema.json','run_manifest.schema.json','suite_ownership.schema.json'}


def _workspace() -> Path:
    """Workspace the requested operation.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace_root(Path(__file__))


def test_wave1_tracked_schema_sources_exist() -> None:
    """Verify that wave1 tracked schema sources exist works as expected.
    """
    # Build filesystem locations and shared state that the rest of
    # test_wave1_tracked_schema_sources_exist reuses.
    source_dir = canonical_schema_source_dir(_workspace())
    assert EXPECTED_CANONICAL_SCHEMA_NAMES <= {p.name for p in source_dir.glob('*.json')}


def test_export_schemas_includes_legacy_and_canonical_contract_sets(capsys) -> None:
    """Verify that export schemas includes legacy and canonical contract
    sets works as expected.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    code = main(['export-schemas', '--project-root', str(workspace)])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['legacy_schema_count'] >= 7
    assert payload['canonical_evolution_schema_count'] == len(EXPECTED_CANONICAL_SCHEMA_NAMES)
    for name in EXPECTED_CANONICAL_SCHEMA_NAMES:
        assert (workspace / 'docs' / 'platform' / 'schemas' / name).is_file()


def test_all_current_suite_ownership_declarations_exist_and_validate() -> None:
    """Verify that all current suite ownership declarations exist and
    validate works as expected.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.
    """
    workspace = _workspace()
    schema = json.loads((workspace / 'fy_platform' / 'contracts' / 'evolution_wave1' / 'schemas' / 'suite_ownership.schema.json').read_text())
    missing = []
    for suite in suite_names_for_ownership(workspace):
        path = workspace / suite / 'suite_ownership.json'
        if not path.is_file():
            missing.append(suite)
            continue
        validate(instance=json.loads(path.read_text()), schema=schema)
    assert missing == []
