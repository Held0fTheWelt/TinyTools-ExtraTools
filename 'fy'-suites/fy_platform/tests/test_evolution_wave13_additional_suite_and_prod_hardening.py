"""Tests for evolution wave13 additional suite and prod hardening.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.security_review import scan_workspace_security
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


def test_templates_usability_and_api_modes_emit_canonical_graph(tmp_path: Path, capsys) -> None:
    """Verify that templates usability and api modes emit canonical graph
    works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    assert main(['analyze', '--mode', 'templates', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_templates_usability_and_api_modes_emit_canonical_graph branches on or
    # transforms it further.
    templates = json.loads(capsys.readouterr().out)
    assert templates['canonical_graph']['unit_count'] > 0

    assert main(['analyze', '--mode', 'usability', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    # Read and normalize the input data before
    # test_templates_usability_and_api_modes_emit_canonical_graph branches on or
    # transforms it further.
    usability = json.loads(capsys.readouterr().out)
    assert usability['canonical_graph']['unit_count'] > 0

    target = tmp_path / 'api_target'
    (target / 'docs' / 'api').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (target / 'docs' / 'api' / 'openapi.yaml').write_text('openapi: 3.0.0\ninfo:\n  title: API\n  version: 1.0.0\npaths: {}\n', encoding='utf-8')
    assert main(['analyze', '--mode', 'api', '--project-root', str(workspace), '--target-repo', str(target)]) == 0
    # Read and normalize the input data before
    # test_templates_usability_and_api_modes_emit_canonical_graph branches on or
    # transforms it further.
    api = json.loads(capsys.readouterr().out)
    assert api['canonical_graph']['unit_count'] > 0


def test_production_security_review_ignores_imported_reference_docs() -> None:
    """Verify that production security review ignores imported reference
    docs works as expected.
    """
    review = scan_workspace_security(_workspace())
    assert review['ok'] is True
    assert review['secret_hit_count'] == 0
