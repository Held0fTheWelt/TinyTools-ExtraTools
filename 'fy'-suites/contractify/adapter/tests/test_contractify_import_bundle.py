"""Tests for contractify import bundle.

"""
from __future__ import annotations

import zipfile
from pathlib import Path

from contractify.adapter.service import ContractifyAdapter


def _build_bundle(tmp_path: Path) -> Path:
    """Build bundle.

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
    base = tmp_path / 'base'
    (base / "'fy'-suites" / 'contractify' / 'reports').mkdir(parents=True)
    (base / "'fy'-suites" / 'contractify' / 'state').mkdir(parents=True)
    (base / 'docs' / 'ADR').mkdir(parents=True)
    (base / 'docs' / 'platform').mkdir(parents=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (base / "'fy'-suites" / 'contractify' / 'reports' / 'contract_audit.json').write_text('{"ok": true}\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (base / 'docs' / 'ADR' / 'ADR-0001.md').write_text('# ADR\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (base / 'docs' / 'platform' / 'X.md').write_text('# Platform\n', encoding='utf-8')
    z = tmp_path / 'bundle.zip'
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when _build_bundle leaves it.
    with zipfile.ZipFile(z, 'w') as zf:
        # Process path one item at a time so _build_bundle applies the same rule across
        # the full collection.
        for path in base.rglob('*'):
            # Branch on path.is_file() so _build_bundle only continues along the
            # matching state path.
            if path.is_file():
                zf.write(path, path.relative_to(tmp_path))
    return z


def test_contractify_import_supports_nested_base_bundle(tmp_path):
    """Verify that contractify import supports nested base bundle works as
    expected.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'fy_governance_enforcement.yaml').write_text('mode: test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('# test\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="x"\nversion="0"\n', encoding='utf-8')
    for req in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
        (tmp_path / req).write_text('\n', encoding='utf-8')
    for rel in ['contractify/README.md','contractify/adapter/service.py','contractify/adapter/cli.py']:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        p.write_text('# x\n', encoding='utf-8')
    for rel in ['contractify/reports','contractify/state','contractify/tools','contractify/templates']:
        (tmp_path / rel).mkdir(parents=True, exist_ok=True)
    adapter = ContractifyAdapter(tmp_path)
    result = adapter.import_bundle(str(_build_bundle(tmp_path)), legacy=False)
    assert result['ok'] is True
    assert result['artifact_count'] >= 1
    assert result['imported_adr_count'] >= 1
