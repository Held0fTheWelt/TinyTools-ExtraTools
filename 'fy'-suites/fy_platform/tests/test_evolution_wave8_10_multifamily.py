"""Tests for evolution wave8 10 multifamily.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.workspace import workspace_root
from fy_platform.tools.cli import main


def _workspace() -> Path:
    """Workspace the requested operation.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace_root(Path(__file__))


def test_contractify_and_testify_emit_multiple_truthful_families(capsys) -> None:
    """Verify that contractify and testify emit multiple truthful families
    works as expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    assert main(['analyze', '--mode', 'contract', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_contractify_and_testify_emit_multiple_truthful_families.
    contract_payload = json.loads(capsys.readouterr().out)
    assert contract_payload['canonical_graph']['family_count'] >= 3
    # Read and normalize the input data before
    # test_contractify_and_testify_emit_multiple_truthful_families branches on or
    # transforms it further.
    contract_export = workspace / contract_payload['canonical_graph']['export_dir']
    normative_inventory = json.loads((contract_export / 'normative_inventory.json').read_text(encoding='utf-8'))
    families = set(normative_inventory['family_counts'])
    assert {'workflow_definition', 'public_command_surface', 'schema_export'} <= families

    assert main(['analyze', '--mode', 'quality', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_contractify_and_testify_emit_multiple_truthful_families.
    quality_payload = json.loads(capsys.readouterr().out)
    assert quality_payload['canonical_graph']['linked_family_count'] >= 2
    # Read and normalize the input data before
    # test_contractify_and_testify_emit_multiple_truthful_families branches on or
    # transforms it further.
    quality_export = workspace / quality_payload['canonical_graph']['export_dir']
    claim_status = json.loads((quality_export / 'claim_proof_status.json').read_text(encoding='utf-8'))
    linked_by_family = claim_status['linked_claims_by_family']
    assert linked_by_family.get('workflow_definition', 0) >= 1
    assert linked_by_family.get('public_command_surface', 0) >= 1
    assert linked_by_family.get('schema_export', 0) >= 1


def test_documentify_compiles_family_aware_outputs(capsys) -> None:
    """Verify that documentify compiles family aware outputs works as
    expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    assert main(['analyze', '--mode', 'code_docs', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'contract', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'quality', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    docs_payload = json.loads(capsys.readouterr().out)
    assert docs_payload['graph_inputs']['shared_evidence_mode'] == 'multi-family-governed-shared-evidence'
    generated_dir = Path(docs_payload['generated_dir'])
    manifest = json.loads((generated_dir / 'document_manifest.json').read_text(encoding='utf-8'))
    assert manifest['graph_inputs']['shared_evidence_mode'] == 'multi-family-governed-shared-evidence'
    assert manifest['graph_inputs']['family_rows']
    assert (generated_dir / 'technical' / 'EVIDENCE_FAMILY_MATRIX.md').is_file()
    assert (generated_dir / 'technical' / 'GOVERNANCE_REFERENCE.md').is_file()
    assert (generated_dir / 'status' / 'EVIDENCE_GAPS.md').is_file()
    easy_overview = (generated_dir / 'easy' / 'OVERVIEW.md').read_text(encoding='utf-8')
    assert 'How this is governed' in easy_overview
    ai_bundle = json.loads((generated_dir / 'ai-read' / 'bundle.json').read_text(encoding='utf-8'))
    assert any(chunk['id'] == 'evidence_families' for chunk in ai_bundle['chunks'])
