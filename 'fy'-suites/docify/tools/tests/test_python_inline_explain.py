"""Tests for python inline explain.

"""
from pathlib import Path

from docify.tools.python_inline_explain import annotate_function_inline, main

SAMPLE = """
def helper():
    json_path = run_dir / f"{role_prefix}.json"
    write_json(json_path, payload)
    self.registry.record_artifact(payload=payload)
    return {"json_path": str(json_path)}
""".lstrip()


def test_annotate_function_inline_adds_contextful_comments() -> None:
    """Verify that annotate function inline adds contextful comments works
    as expected.
    """
    rendered = annotate_function_inline(SAMPLE, 'helper', mode='dense')
    assert 'Build filesystem locations' in rendered
    assert 'Persist the structured JSON representation' in rendered
    assert 'Register the written artifact in the evidence registry' in rendered


def test_inline_explain_cli_writes_output(tmp_path: Path) -> None:
    """Verify that inline explain cli writes output works as expected.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.
    """
    src = tmp_path / 'sample.py'
    out = tmp_path / 'annotated.py'
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    src.write_text(SAMPLE, encoding='utf-8')
    code = main(['--file', str(src), '--function', 'helper', '--output', str(out)])
    assert code == 0
    text = out.read_text(encoding='utf-8')
    assert 'Build filesystem locations' in text



def test_annotate_function_inline_is_idempotent_for_existing_blocks() -> None:
    """Verify that annotate function inline is idempotent for existing
    blocks works as expected.
    """
    source = """class Example:
    def helper(self, value: int) -> int:
        result = value + 1
        if result > 3:
            return result
        return value
"""
    first = annotate_function_inline(source, 'Example.helper')
    second = annotate_function_inline(first, 'Example.helper')
    assert first == second
    assert first.count('Branch on result > 3') == 1
    assert 'Prepare the local state' not in first


def test_annotate_function_inline_accepts_qualified_method_names() -> None:
    """Verify that annotate function inline accepts qualified method names
    works as expected.
    """
    source = """class Example:
    def helper(self, value: int) -> dict[str, str]:
        json_path = run_dir / f"{value}.json"
        return {"json_path": str(json_path)}
"""
    rendered = annotate_function_inline(source, 'Example.helper')
    assert 'Build filesystem locations' in rendered


def test_annotate_function_inline_replaces_old_generated_blocks() -> None:
    """Verify that annotate function inline replaces old generated
    blocks works as expected.
    """
    source = """def helper():
    json_path = run_dir / "out.json"
    write_json(json_path, payload)
"""
    rendered = annotate_function_inline(source, 'helper')
    assert 'Prepare the local state' not in rendered
    assert 'Build filesystem locations' in rendered

