"""Tests for contractify imports.

"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from contractify.adapter.service import ContractifyAdapter


def _make_bundle(tmp_path: Path, *, legacy: bool) -> Path:
    """Make bundle.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
        legacy: Whether to enable this optional behavior.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    src = tmp_path / ('legacy_bundle' if legacy else 'current_bundle')
    root = src
    # Branch on not legacy so _make_bundle only continues along the matching state path.
    if not legacy:
        (root / 'fy_platform').mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        (root / 'pyproject.toml').write_text('[project]\nname="fy-suites"\nversion="1.0.0"\n', encoding='utf-8')
        # Build filesystem locations and shared state that the rest of _make_bundle
        # reuses.
        adr_dir = root / 'docs' / 'ADR'
    else:
        adr_dir = root / "'fy'-suites" / 'docs' / 'ADR'
    (root / 'contractify' / 'reports').mkdir(parents=True, exist_ok=True)
    adr_dir.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'contractify' / 'reports' / 'contract_audit.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (adr_dir / 'ADR-0001-example.md').write_text('# ADR-0001\n\nExample\n', encoding='utf-8')
    bundle = tmp_path / ('legacy_bundle.zip' if legacy else 'current_bundle.zip')
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when _make_bundle leaves it.
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Process item one item at a time so _make_bundle applies the same rule across
        # the full collection.
        for item in src.rglob('*'):
            # Branch on item.is_dir() so _make_bundle only continues along the matching
            # state path.
            if item.is_dir():
                continue
            zf.write(item, arcname=str(item.relative_to(src)))
    return bundle


def _make_workspace(tmp_path: Path) -> Path:
    """Make workspace.

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
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (workspace / 'fy_governance_enforcement.yaml').write_text('enforce: true\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (workspace / 'README.md').write_text('# fy\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (workspace / 'pyproject.toml').write_text('[project]\nname="fy-suites"\nversion="1.0.0"\n', encoding='utf-8')
    for name in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
        (workspace / name).write_text('', encoding='utf-8')
    suite = workspace / 'contractify'
    for rel in ['adapter', 'tools', 'reports', 'state', 'templates']:
        (suite / rel).mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'README.md').write_text('# contractify\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'adapter' / 'service.py').write_text('class X: pass\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (suite / 'adapter' / 'cli.py').write_text('def main():\n    return 0\n', encoding='utf-8')
    return workspace


def test_contractify_imports_current_bundle(tmp_path: Path) -> None:
    """Verify that contractify imports current bundle works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    workspace = _make_workspace(tmp_path)
    adapter = ContractifyAdapter(workspace)
    bundle = _make_bundle(tmp_path, legacy=False)
    result = adapter.import_bundle(str(bundle), legacy=False)
    assert result['ok'] is True
    assert result['bundle_layout'] in {'current', 'legacy-request-current-shape'}
    assert result['artifact_count'] >= 1


def test_contractify_imports_legacy_bundle(tmp_path: Path) -> None:
    """Verify that contractify imports legacy bundle works as expected.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    workspace = _make_workspace(tmp_path)
    adapter = ContractifyAdapter(workspace)
    bundle = _make_bundle(tmp_path, legacy=True)
    result = adapter.import_bundle(str(bundle), legacy=True)
    assert result['ok'] is True
    assert result['bundle_layout'].startswith('legacy')
    assert result['imported_adr_count'] >= 1
