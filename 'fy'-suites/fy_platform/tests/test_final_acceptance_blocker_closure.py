"""Tests for final acceptance blocker closure.

"""
from __future__ import annotations

import json
import zipfile
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


def _build_rich_import_zip(tmp_path: Path) -> Path:
    """Build rich import zip.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    src = tmp_path / 'bundle' / 'rich'
    (src / 'docs' / 'ADR').mkdir(parents=True)
    (src / 'schemas').mkdir(parents=True)
    (src / 'examples').mkdir(parents=True)
    (src / '09_TOOL_SPECS').mkdir(parents=True)
    (src / 'ir').mkdir(parents=True)
    (src / 'ai').mkdir(parents=True)
    (src / 'bootstrap').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'docs' / 'ADR' / 'ADR-0001.md').write_text('# ADR\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'schemas' / 'artifact.schema.json').write_text('{}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'examples' / 'workflow_graph_example.json').write_text('{"ok": true}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / '09_TOOL_SPECS' / '09A_PLATFORM_SPEC.md').write_text('# Spec\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'ir' / 'graph.json').write_text('{"nodes": []}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'ai' / 'context_pack.json').write_text('{"purpose": "demo"}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'bootstrap' / 'starter.py').write_text('print("hi")\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / '12_PHASED_IMPLEMENTATION_PROGRAM.md').write_text('# Task\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'MANIFEST.txt').write_text('manifest\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (src / 'README.md').write_text('# Imported MVP\n', encoding='utf-8')
    z = tmp_path / 'rich.zip'
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when _build_rich_import_zip leaves it.
    with zipfile.ZipFile(z, 'w') as zf:
        # Process path one item at a time so _build_rich_import_zip applies the same
        # rule across the full collection.
        for path in src.rglob('*'):
            # Branch on path.is_file() so _build_rich_import_zip only continues along
            # the matching state path.
            if path.is_file():
                zf.write(path, path.relative_to(src))
    return z


def test_mvpify_materially_preserves_rich_import_content(tmp_path: Path, capsys) -> None:
    """Verify that mvpify materially preserves rich import content works as
    expected.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    bundle = _build_rich_import_zip(tmp_path)
    assert main(['import', '--mode', 'mvp', '--project-root', str(workspace), '--bundle', str(bundle)]) == 0
    payload = json.loads(capsys.readouterr().out)
    report = json.loads(Path(payload['json_path']).read_text(encoding='utf-8'))
    inv = report['import_inventory']
    assert inv['preserved_file_count'] >= 8
    classes = inv['preserved_class_counts']
    for required in ['docs', 'schemas', 'examples', 'tool_specs', 'ai_context', 'ir', 'bootstrap', 'root_docs']:
        assert classes.get(required, 0) >= 1, required
    normalized = workspace / inv['normalized_source_tree']
    assert (normalized / '09_TOOL_SPECS' / '09A_PLATFORM_SPEC.md').is_file()
    assert (normalized / 'schemas' / 'artifact.schema.json').is_file()
    assert (normalized / 'examples' / 'workflow_graph_example.json').is_file()
    mirrored = workspace / inv['mirrored_docs_root']
    assert (mirrored / 'README.md').is_file()
    assert (mirrored / 'docs' / 'ADR' / 'ADR-0001.md').is_file()


def test_documentify_surfaces_richer_mvpify_import_context(tmp_path: Path, capsys) -> None:
    """Verify that documentify surfaces richer mvpify import context works
    as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    bundle = _build_rich_import_zip(tmp_path)
    assert main(['import', '--mode', 'mvp', '--project-root', str(workspace), '--bundle', str(bundle)]) == 0
    _ = capsys.readouterr().out
    assert main(['analyze', '--mode', 'docs', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    docs = json.loads(capsys.readouterr().out)
    generated_dir = Path(docs['generated_dir'])
    manifest = json.loads((generated_dir / 'document_manifest.json').read_text(encoding='utf-8'))
    assert manifest['graph_inputs']['mvpify']['available'] is True
    tech = (generated_dir / 'technical' / 'MVP_IMPORT_REFERENCE.md').read_text(encoding='utf-8')
    assert 'preserved_file_count' in tech
    assert 'Preserved classes' in tech
    ai_bundle = json.loads((generated_dir / 'ai-read' / 'bundle.json').read_text(encoding='utf-8'))
    assert any(chunk['id'] == 'mvp_import_classes' for chunk in ai_bundle['chunks'])


def test_security_review_and_production_readiness_are_aligned(capsys) -> None:
    """Verify that security review and production readiness are aligned
    works as expected.

    Args:
        capsys: Primary capsys used by this step.
    """
    workspace = _workspace()
    review = scan_workspace_security(workspace)
    assert review['ok'] is True
    assert review['security_doc_count'] >= 1
    assert review['has_gitignore'] is True
    assert review['ignore_has_secret_rules'] is True
    assert main(['analyze', '--mode', 'security', '--project-root', str(workspace), '--target-repo', str(workspace)]) == 0
    sec = json.loads(capsys.readouterr().out)
    assert sec['security_ok'] is True
    assert main(['production-readiness', '--project-root', str(workspace)]) == 0
    prod = json.loads(capsys.readouterr().out)
    assert prod['ok'] is True
    assert prod['security']['ok'] is True
