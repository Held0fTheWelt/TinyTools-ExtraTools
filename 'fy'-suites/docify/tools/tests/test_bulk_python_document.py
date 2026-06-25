"""Tests for bulk python document.

"""
from __future__ import annotations

from pathlib import Path

from docify.tools.bulk_python_document import run_documentation_pass


def test_run_documentation_pass_documents_repo_and_is_rerun_safe(tmp_path: Path) -> None:
    """Verify that run documentation pass documents repo and is rerun safe
    works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    source = tmp_path / 'sample.py'
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    source.write_text(
        """\
class DemoService:
    def build_payload(self, path: str) -> dict[str, str]:
        json_path = Path(path)
        payload = {"path": str(json_path)}
        write_json(json_path, payload)
        return payload


def main(argv: list[str]) -> int:
    result = len(argv)
    return result
""",
        encoding='utf-8',
    )

    summary, updates = run_documentation_pass(
        repo_root=tmp_path,
        root=tmp_path,
        include_tests=True,
    )
    assert summary.changed_files == 1
    assert updates[0].module_docstring_added is True
    # Read and normalize the input data before
    # test_run_documentation_pass_documents_repo_and_is_rerun_safe branches on or
    # transforms it further.
    rendered = source.read_text(encoding='utf-8')
    assert 'Package exports' not in rendered
    assert 'Service object for demo operations.' in rendered
    assert 'Run the command-line entry point.' in rendered
    assert 'Build filesystem locations' in rendered
    assert 'Persist the structured JSON representation' in rendered

    second_summary, second_updates = run_documentation_pass(
        repo_root=tmp_path,
        root=tmp_path,
        include_tests=True,
    )
    assert second_summary.changed_files == 0
    assert second_updates == []
