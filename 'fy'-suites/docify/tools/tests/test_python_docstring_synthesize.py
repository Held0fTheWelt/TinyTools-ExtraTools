"""Tests for python docstring synthesize.

"""
from __future__ import annotations

import ast

from docify.tools.python_docstring_synthesize import (
    _attach_parents,
    apply_google_docstring_to_class_node,
    apply_function_google_docstring,
    apply_module_google_docstring,
)


def test_apply_function_google_docstring_avoids_placeholder_phrases() -> None:
    """Verify that apply function google docstring avoids placeholder
    phrases works as expected.
    """
    source = """\
def build_result(path: str, payload: dict[str, str]) -> dict[str, str]:
    return payload
"""
    new_source, error = apply_function_google_docstring(source, "build_result")
    assert error is None
    assert new_source is not None
    assert "meaning follows the type and call sites" not in new_source
    assert "Behaviour, edge cases, and invariants should be inferred" not in new_source
    assert "Args:" in new_source
    assert "Returns:" in new_source


def test_apply_google_docstring_to_class_node_uses_class_summary() -> None:
    """Verify that apply google docstring to class node uses class summary
    works as expected.
    """
    source = """\
class DemoService:
    def run(self) -> None:
        return None
"""
    tree = ast.parse(source)
    _attach_parents(tree)
    node = next(item for item in ast.walk(tree) if isinstance(item, ast.ClassDef))
    new_source, error = apply_google_docstring_to_class_node(source, node)
    assert error is None
    assert new_source is not None
    assert "Service object for demo operations." in new_source


def test_apply_module_google_docstring_uses_module_summary() -> None:
    """Verify that apply module google docstring uses module summary works
    as expected.
    """
    source = """\
def helper() -> None:
    return None
"""
    new_source, error = apply_module_google_docstring(
        source,
        rel_posix="package/service.py",
    )
    assert error is None
    assert new_source is not None
    assert "Service helpers for package." in new_source
