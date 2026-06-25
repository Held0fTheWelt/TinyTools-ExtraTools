"""Tests for document builder.

"""
import json
import shutil

from documentify.tools.document_builder import generate_documentation
from documentify.tools.hub_cli import main
from documentify.tools.repo_paths import repo_root


def test_generate_documentation_materializes_expected_views() -> None:
    """Verify that generate documentation materializes expected views works
    as expected.
    """
    # Build filesystem locations and shared state that the rest of
    # test_generate_documentation_materializes_expected_views reuses.
    root = repo_root()
    out_dir = root / "'fy'-suites" / 'documentify' / 'generated'
    summary = generate_documentation(root, out_dir)
    assert summary['generated_count'] >= 7
    assert summary['simple_style'] == 'what-why-how'
    assert summary['uses_mermaid'] is True
    # Read and normalize the input data before
    # test_generate_documentation_materializes_expected_views branches on or transforms
    # it further.
    text = (out_dir / 'simple' / 'PLATFORM_OVERVIEW.md').read_text(encoding='utf-8')
    assert '## What is it?' in text
    assert '## Why does it exist?' in text
    assert '```mermaid' in text
    assert (out_dir / 'roles' / 'developer' / 'README.md').is_file()


def test_cli_writes_reports() -> None:
    """Verify that cli writes reports works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = repo_root()
    out = root / "'fy'-suites" / 'documentify' / 'reports' / '_pytest_documentify_audit.json'
    md = root / "'fy'-suites" / 'documentify' / 'reports' / '_pytest_documentify_audit.md'
    gen = root / "'fy'-suites" / 'documentify' / '_pytest_generated'
    try:
        code = main(['generate', '--out-dir', gen.relative_to(root).as_posix(), '--out', out.relative_to(root).as_posix(), '--md-out', md.relative_to(root).as_posix(), '--quiet'])
        assert code == 0
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['suite'] == 'documentify'
        assert data['simple_style'] == 'what-why-how'
        assert md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if md.is_file():
            md.unlink()
        if gen.exists():
            shutil.rmtree(gen)
