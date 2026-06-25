#!/usr/bin/env python3
"""
Remove bulk-docstring placeholder prose from ``ai_stack`` (excluding
``tests/``).

Rewrites only string literals that are the leading docstring of
``Module``, ``ClassDef``, ``FunctionDef``, or ``AsyncFunctionDef``
nodes. Does **not** change ``# TODO`` comments or non-docstring string
literals.

Run from repository root::

python
"./'fy'-suites/docify/tools/strip_ai_stack_docstring_placeholders.py"
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from python_docstring_synthesize import (  # noqa: E402
    format_function_docstring_from_dedented_body,
    format_top_module_docstring_block,
)


def _replace_split_todo_document(text: str) -> str:
    """Handle ``name: TODO: document\n ``name`` (type...).`` (name repeated
    on next line).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    pattern = re.compile(r"([A-Za-z_]\w*): TODO: document\s*\n\s*``\1`` \(", re.MULTILINE)
    pos = 0
    chunks: list[str] = []
    # Stay in this loop only while True remains true, so callers do not observe a
    # half-finished _replace_split_todo_document state.
    while True:
        m = pattern.search(text, pos)
        # Branch on not m so _replace_split_todo_document only continues along the
        # matching state path.
        if not m:
            chunks.append(text[pos:])
            break
        chunks.append(text[pos : m.start()])
        open_paren = m.end() - 1
        depth = 0
        k = open_paren
        # Stay in this loop only while k < len(text) remains true, so callers do not
        # observe a half-finished _replace_split_todo_document state.
        while k < len(text):
            ch = text[k]
            # Branch on ch == '(' so _replace_split_todo_document only continues along
            # the matching state path.
            if ch == "(":
                depth += 1
            # Branch on ch == ')' so _replace_split_todo_document only continues along
            # the matching state path.
            elif ch == ")":
                depth -= 1
                # Branch on depth == 0 so _replace_split_todo_document only continues
                # along the matching state path.
                if depth == 0:
                    k += 1
                    break
            k += 1
        # Branch on depth != 0 so _replace_split_todo_document only continues along the
        # matching state path.
        if depth != 0:
            chunks.append(text[pos : m.end()])
            pos = m.end()
            continue
        type_slice = text[open_paren:k]
        dot = ""
        # Branch on k < len(text) and text[k] == '.' so _replace_split_todo_document
        # only continues along the matching state path.
        if k < len(text) and text[k] == ".":
            dot = "."
            k += 1
        name = m.group(1)
        chunks.append(f"{name}: ``{name}`` {type_slice}; meaning follows the type and call sites{dot}")
        pos = k
    return "".join(chunks)


def _replace_todo_document_balanced(text: str) -> str:
    """Turn ``TODO: document ``name`` (type...).`` into neutral Arg prose.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    key = "TODO: document ``"
    out_parts: list[str] = []
    pos = 0
    while True:
        i = text.find(key, pos)
        if i == -1:
            out_parts.append(text[pos:])
            break
        out_parts.append(text[pos:i])
        j = i + len(key)
        end_name = text.find("``", j)
        if end_name == -1:
            out_parts.append(text[i:])
            break
        name = text[j:end_name]
        k = end_name + 2
        while k < len(text) and text[k] in " \t\n\r":
            k += 1
        if k >= len(text) or text[k] != "(":
            out_parts.append(text[i : i + len(key)])
            pos = i + len(key)
            continue
        depth = 0
        k2 = k
        while k2 < len(text):
            ch = text[k2]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    k2 += 1
                    break
            k2 += 1
        if depth != 0:
            out_parts.append(text[i : i + len(key)])
            pos = i + len(key)
            continue
        type_str = text[k:k2]
        dot = ""
        if k2 < len(text) and text[k2] == ".":
            dot = "."
            k2 += 1
        repl = f"``{name}`` {type_str}; meaning follows the type and call sites{dot}"
        out_parts.append(repl)
        pos = k2
    return "".join(out_parts)


def _sanitize_docstring_inner(inner: str) -> str:
    """Transform *inner* (``ast.get_docstring(..., clean=True)`` body).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        inner: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    s = inner

    s = re.sub(
        r"TODO: describe the return value shape,\s*caller\s*\n\s*expectations, and any failure or sentinel cases\s*\n\s*for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(
        r"TODO: describe the return value shape, caller\s+expectations, and any\s+failure or sentinel cases\s+for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"TODO: describe the return value\s*\n\s*shape, caller expectations, and\s*\n\s*any failure or sentinel cases\s*\n\s*for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(
        r"TODO: describe the return value shape,\s*\n\s*caller\s+expectations, and any failure or\s*\n\s*sentinel cases\s*\n\s*for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(
        r"TODO: describe the return value shape,\s*\n\s*caller expectations, and any\s*\n\s*failure or sentinel cases\s*\n\s*for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(
        r"TODO: describe the return value shape,\s*\n\s*caller expectations, and any failure or\s*\n\s*sentinel cases for ``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(
        r"TODO: describe the return value shape,\s*\n\s*caller expectations, and any failure or\s*\n\s*sentinel cases for\s*\n\s*``([^`]+)``\.",
        r"Returns a value of type ``\1``; see the function body for structure, error paths, and sentinels.",
        s,
        flags=re.MULTILINE,
    )

    s = re.sub(
        r"Replace this paragraph with behaviour, edge cases, and invariants\.\s*Keep English concise; tighten wording before merge\.",
        "Behaviour, edge cases, and invariants should be inferred from the "
        "implementation and public contract of this symbol.",
        s,
    )
    s = re.sub(
        r"Replace this paragraph with behaviour, edge cases, and\s*\n\s*invariants\. Keep English concise; tighten wording before\s*\n\s*merge\.",
        "Behaviour, edge cases, and invariants should be inferred from the "
        "implementation and public contract of this symbol.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"Replace this paragraph with behaviour, edge cases, and\s*\n\s*invariants\. Keep English concise; tighten wording before merge\.",
        "Behaviour, edge cases, and invariants should be inferred from the "
        "implementation and public contract of this symbol.",
        s,
        flags=re.MULTILINE,
    )

    s = re.sub(
        r"Describe what ``([^`]+)`` does in one line \(verb-led\s*\n\s*summary for this (?:function|method)\)\.",
        r"``\1`` — see implementation for behaviour and contracts.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"Describe what ``([^`]+)`` does in one line \(verb-led summary\s*\n\s*for this (?:function|method)\)\.",
        r"``\1`` — see implementation for behaviour and contracts.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"Describe what ``([^`]+)`` does in one line \(verb-led summary for this (?:function|method)\)\.",
        r"``\1`` — see implementation for behaviour and contracts.",
        s,
    )

    s = re.sub(
        r"TODO: document ``([^`]+)`` responsibilities, invariants, and any\s+thread-safety expectations for callers\.",
        r"``\1`` groups related behaviour; callers should read members for contracts and threading assumptions.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"TODO: document ``([^`]+)`` responsibilities, invariants, and\s*\n\s*any thread-safety expectations for callers\.",
        r"``\1`` groups related behaviour; callers should read members for contracts and threading assumptions.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"TODO: document ``([^`]+)`` responsibilities, invariants,\s*\n\s*and any thread-safety expectations for callers\.",
        r"``\1`` groups related behaviour; callers should read members for contracts and threading assumptions.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"TODO: document ``([^`]+)`` responsibilities,\s*\n\s*invariants, and any thread-safety expectations for callers\.",
        r"``\1`` groups related behaviour; callers should read members for contracts and threading assumptions.",
        s,
        flags=re.DOTALL,
    )

    s = re.sub(
        r"``([^`]+)`` — expand purpose, primary entrypoints,\s*\n\s*and invariants for maintainers\.",
        r"``\1`` — public surface of this module; see exports and call sites for contracts.",
        s,
        flags=re.DOTALL,
    )
    s = re.sub(
        r"``([^`]+)`` — expand purpose, primary entrypoints, and invariants for maintainers\.",
        r"``\1`` — public surface of this module; see exports and call sites for contracts.",
        s,
    )

    while "TODO: document ``" in s:
        s2 = _replace_todo_document_balanced(s)
        if s2 == s:
            break
        s = s2

    while True:
        s2 = _replace_split_todo_document(s)
        if s2 == s:
            break
        s = s2

    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def _leading_docstring_spans(tree: ast.Module) -> list[tuple[ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, ast.Expr]]:
    """Leading docstring spans.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        tree: Parsed AST object being inspected or transformed.

    Returns:
        list[tuple[ast.Module | ast.ClassDef | ast.FunctionDef | as...:
            Collection produced from the parsed or
            accumulated input data.
    """
    spans: list[tuple[ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, ast.Expr]] = []

    def maybe(node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Maybe the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        if not node.body:
            return
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(
            first.value.value, str
        ):
            spans.append((node, first))

    maybe(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            maybe(n)
    return spans


def _content_indent_for_stmt(raw_lines: list[str], expr: ast.Expr) -> str:
    """Content indent for stmt.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        raw_lines: Primary raw lines used by this step.
        expr: Primary expr used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    idx = (expr.lineno or 1) - 1
    if 0 <= idx < len(raw_lines):
        raw = raw_lines[idx]
        return raw[: len(raw) - len(raw.lstrip())]
    return ""


def _rewrite_source_docstrings(source: str) -> tuple[str, int]:
    """Rewrite source docstrings.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        source: Text content to inspect or rewrite.

    Returns:
        tuple[str, int]:
            Collection produced from the parsed or
            accumulated input data.
    """
    total = 0
    while True:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source, total
        raw_lines = source.splitlines(keepends=True)
        spans = _leading_docstring_spans(tree)
        picked: tuple[
            ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
            ast.Expr,
            str,
        ] | None = None
        for owner, expr in sorted(spans, key=lambda t: -((t[1].lineno or 1))):
            dedented = ast.get_docstring(owner, clean=True) or ""
            if not dedented.strip():
                continue
            new_inner = _sanitize_docstring_inner(dedented)
            if new_inner.rstrip() == dedented.rstrip():
                continue
            picked = (owner, expr, new_inner)
            break
        if picked is None:
            break
        owner, expr, new_inner = picked
        ci = _content_indent_for_stmt(raw_lines, expr)
        inner_stripped = new_inner.strip("\n")
        if isinstance(owner, ast.Module) and not ci.strip():
            new_stmt = format_top_module_docstring_block(inner_stripped)
        else:
            new_stmt = format_function_docstring_from_dedented_body(inner_stripped, ci)
        new_lines = new_stmt.splitlines(keepends=True)
        start = (expr.lineno or 1) - 1
        end = (expr.end_lineno or expr.lineno or 1) - 1
        source = "".join(raw_lines[:start] + new_lines + raw_lines[end + 1 :])
        total += 1
    return source, total


def iter_ai_stack_py(repo: Path) -> list[Path]:
    """Yield ai stack py.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    root = repo / "ai_stack"
    out: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        try:
            i = path.parts.index("ai_stack")
        except ValueError:
            continue
        if i + 1 < len(path.parts) and path.parts[i + 1] == "tests":
            continue
        out.append(path)
    return out


def main() -> int:
    """Run the command-line entry point.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = _REPO_ROOT
    files_changed = 0
    edits = 0
    for path in iter_ai_stack_py(repo):
        text = path.read_text(encoding="utf-8-sig")
        new_text, n = _rewrite_source_docstrings(text)
        edits += n
        if new_text != text:
            files_changed += 1
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"files_changed={files_changed}  docstring_passes={edits}  dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
