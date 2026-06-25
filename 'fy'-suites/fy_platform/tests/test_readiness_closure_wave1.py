"""Tests for readiness-and-closure wave 1 surfaces."""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.final_product import command_reference_payload, export_contract_schemas, suite_catalog_payload
from fy_platform.ai.workspace import workspace_root
from fy_platform.runtime.mode_registry import get_mode_spec



def test_diagnosta_is_in_catalog_and_command_reference() -> None:
    workspace = workspace_root(Path(__file__))
    catalog = suite_catalog_payload(workspace)
    suites = {row['suite'] for row in catalog['suites']}
    assert 'diagnosta' in suites
    assert 'coda' in suites
    reference = command_reference_payload(workspace)
    assert 'diagnosta' in reference['suite_native_commands']
    assert 'readiness-case' in reference['suite_native_commands']['diagnosta']
    assert reference['active_strategy_profile']['active_profile'] == 'D'
    assert 'strategy show' in reference['platform_native_commands']
    assert 'coda' in reference['suite_native_commands']
    assert 'closure-pack' in reference['suite_native_commands']['coda']



def test_exported_schemas_include_readiness_and_strategy_surfaces(tmp_path: Path) -> None:
    workspace = workspace_root(Path(__file__))
    payload = export_contract_schemas(workspace)
    written = set(payload['written_paths'])
    assert 'docs/platform/schemas/readiness_case.schema.json' in written
    assert 'docs/platform/schemas/blocker_graph.schema.json' in written
    assert 'docs/platform/schemas/active_strategy_profile.schema.json' in written



def test_mode_registry_exposes_readiness_modes() -> None:
    assert get_mode_spec('analyze', 'readiness').suite == 'diagnosta'
    assert get_mode_spec('inspect', 'readiness').suite == 'diagnosta'
    assert get_mode_spec('analyze', 'closure').suite == 'coda'
    assert get_mode_spec('inspect', 'closure').suite == 'coda'
