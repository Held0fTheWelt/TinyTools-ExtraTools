"""Tests for evolution wave11 broad suite participation.

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


def test_public_surfaces_emit_broad_suite_graph_slices(capsys) -> None:
    """Verify that public surfaces emit broad suite graph slices works as
    expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    assert main(['analyze', '--mode', 'security', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_public_surfaces_emit_broad_suite_graph_slices branches on or transforms it
    # further.
    sec = json.loads(capsys.readouterr().out)
    assert sec['canonical_graph']['unit_count'] >= 2

    assert main(['analyze', '--mode', 'structure', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_public_surfaces_emit_broad_suite_graph_slices branches on or transforms it
    # further.
    des = json.loads(capsys.readouterr().out)
    assert des['canonical_graph']['unit_count'] >= 2

    assert main(['analyze', '--mode', 'docker', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_public_surfaces_emit_broad_suite_graph_slices branches on or transforms it
    # further.
    docker = json.loads(capsys.readouterr().out)
    assert docker['canonical_graph']['artifact_count'] >= 4

    assert main(['analyze', '--mode', 'observability', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_public_surfaces_emit_broad_suite_graph_slices branches on or transforms it
    # further.
    obs = json.loads(capsys.readouterr().out)
    assert obs['canonical_graph']['unit_count'] >= 1

    assert main(['metrics', '--mode', 'report', '--project-root', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_public_surfaces_emit_broad_suite_graph_slices branches on or transforms it
    # further.
    metrify = json.loads(capsys.readouterr().out)
    assert metrify['canonical_graph']['artifact_count'] >= 4


def test_documentify_reflects_broad_suite_participation(capsys) -> None:
    """Verify that documentify reflects broad suite participation works as
    expected.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    for mode in ('security', 'structure', 'docker', 'observability'):
        assert main(['analyze', '--mode', mode, '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
        _ = capsys.readouterr().out
    assert main(['metrics', '--mode', 'report', '--project-root', str(workspace)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    docs = json.loads(capsys.readouterr().out)
    generated_dir = Path(docs['generated_dir'])
    manifest = json.loads((generated_dir / 'document_manifest.json').read_text(encoding='utf-8'))
    for suite in ('securify', 'despaghettify', 'dockerify', 'observifyfy', 'metrify'):
        assert manifest['graph_inputs'][suite]['available'] is True
    assert (generated_dir / 'technical' / 'BROAD_SUITE_PARTICIPATION.md').is_file()
    assert (generated_dir / 'status' / 'OPERATIONS_AND_RISK_SUMMARY.md').is_file()
