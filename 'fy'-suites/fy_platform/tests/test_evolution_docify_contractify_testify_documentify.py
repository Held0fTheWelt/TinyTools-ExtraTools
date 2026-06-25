"""Tests for evolution docify contractify testify documentify.

"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from fy_platform.ai.workspace import workspace_root
from fy_platform.ai.evolution_contract_pack import canonical_schema_payloads
from fy_platform.tests.fixtures_autark import create_target_repo
from fy_platform.tools.cli import main


def _workspace() -> Path:
    """Workspace the requested operation.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return workspace_root(Path(__file__))


def test_public_surfaces_emit_and_consume_shared_graph(tmp_path: Path, capsys) -> None:
    """Verify that public surfaces emit and consume shared graph works as
    expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    workspace = _workspace()

    assert main(['analyze', '--mode', 'contract', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_public_surfaces_emit_and_consume_shared_graph.
    contract_payload = json.loads(capsys.readouterr().out)
    assert contract_payload['canonical_graph']['claim_count'] > 0

    assert main(['analyze', '--mode', 'quality', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_public_surfaces_emit_and_consume_shared_graph.
    quality_payload = json.loads(capsys.readouterr().out)
    assert quality_payload['canonical_graph']['linked_claim_count'] >= 1
    assert quality_payload['canonical_graph']['contractify_graph_available'] is True

    assert main(['analyze', '--mode', 'code_docs', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_public_surfaces_emit_and_consume_shared_graph.
    code_payload = json.loads(capsys.readouterr().out)
    assert code_payload['canonical_graph']['unit_count'] > 0

    assert main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    # Assemble the structured result data before later steps enrich or return it from
    # test_public_surfaces_emit_and_consume_shared_graph.
    docs_payload = json.loads(capsys.readouterr().out)
    assert docs_payload['graph_inputs']['shared_evidence_mode'] in {'proof-backed', 'governed-shared-evidence'}
    # Build filesystem locations and shared state that the rest of
    # test_public_surfaces_emit_and_consume_shared_graph reuses.
    generated_dir = Path(docs_payload['generated_dir'])
    manifest = json.loads((generated_dir / 'document_manifest.json').read_text())
    assert manifest['graph_inputs']['contractify']['available'] is True
    assert manifest['graph_inputs']['testify']['available'] is True
    assert (generated_dir / 'technical' / 'EVIDENCE_STATUS.md').is_file()
    assert (generated_dir / 'technical' / 'COVERAGE_MATRIX.md').is_file()
    assert (generated_dir / 'status' / 'STALE_REPORT.md').is_file()
    # Read and normalize the input data before
    # test_public_surfaces_emit_and_consume_shared_graph branches on or transforms it
    # further.
    ai_bundle = json.loads((generated_dir / 'ai-read' / 'bundle.json').read_text())
    chunk_ids = {c['id'] for c in ai_bundle['chunks']}
    assert {'normative_graph','proof_graph'} <= chunk_ids


def test_emitted_records_validate_against_canonical_schemas(tmp_path: Path, capsys) -> None:
    """Verify that emitted records validate against canonical schemas works
    as expected.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    repo = create_target_repo(tmp_path)
    workspace = _workspace()
    schemas = canonical_schema_payloads(workspace)

    assert main(['analyze', '--mode', 'contract', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    contract_payload = json.loads(capsys.readouterr().out)
    export_dir = workspace / contract_payload['canonical_graph']['export_dir']
    for unit in json.loads((export_dir / 'unit_index.json').read_text())['units']:
        validate(instance=unit, schema=schemas['fy_unit.schema.json'])
    for rel in json.loads((export_dir / 'relation_graph.json').read_text())['relations']:
        validate(instance=rel, schema=schemas['relation.schema.json'])
    for art in json.loads((export_dir / 'artifact_index.json').read_text())['artifacts']:
        validate(instance=art, schema=schemas['artifact.schema.json'])
    validate(instance=json.loads((export_dir / 'run_manifest.json').read_text()), schema=schemas['run_manifest.schema.json'])

    assert main(['analyze', '--mode', 'quality', '--project-root', str(workspace), '--target-repo', str(repo)]) == 0
    quality_payload = json.loads(capsys.readouterr().out)
    export_dir = workspace / quality_payload['canonical_graph']['export_dir']
    proof_units = json.loads((export_dir / 'unit_index.json').read_text())['units']
    assert any(u['entity_type'] == 'proof' for u in proof_units)
    proof_relations = json.loads((export_dir / 'relation_graph.json').read_text())['relations']
    assert any(r['relation_type'] == 'validates' for r in proof_relations)
