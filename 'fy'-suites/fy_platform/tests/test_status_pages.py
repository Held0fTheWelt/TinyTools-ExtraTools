"""Tests for status pages.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.base_adapter import BaseSuiteAdapter


class DummyAdapter(BaseSuiteAdapter):
    """Adapter implementation for dummy workflows.
    """
    def __init__(self, root: Path) -> None:
        """Initialize DummyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('documentify', root)

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        return self._attach_status_page('audit', {'ok': True, 'suite': self.suite, 'finding_count': 2, 'summary': 'Two issues need attention.'})


def test_status_page_written(tmp_path: Path) -> None:
    """Verify that status page written works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (tmp_path / 'README.md').write_text('x', encoding='utf-8')
    (tmp_path / 'fy_platform').mkdir()
    (tmp_path / 'documentify').mkdir()
    (tmp_path / 'documentify' / 'reports').mkdir(parents=True)
    (tmp_path / 'documentify' / 'state').mkdir(parents=True)
    (tmp_path / 'documentify' / 'generated').mkdir(parents=True)
    # Assemble the structured result data before later steps enrich or return it from
    # test_status_page_written.
    adapter = DummyAdapter(tmp_path)
    payload = adapter.audit(str(tmp_path))
    assert 'status_md_path' in payload
    # Build filesystem locations and shared state that the rest of
    # test_status_page_written reuses.
    md_path = tmp_path / payload['status_md_path']
    assert md_path.is_file()
    # Read and normalize the input data before test_status_page_written branches on or
    # transforms it further.
    text = md_path.read_text(encoding='utf-8')
    assert 'Most-Recent-Next-Steps' in text
    assert 'Two issues need attention.' in text
