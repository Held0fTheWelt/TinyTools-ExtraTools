#!/usr/bin/env python3
"""
Document a Python source tree with Docify-generated docstrings and
comments.

This command is the repo-wide orchestrator for Docify. It keeps one
toolchain:

- ``python_docstring_synthesize.py`` supplies module/class/function
docstrings - ``python_inline_explain.py`` supplies grouped inline
comments for longer flows - the batch runner applies both across a
selected source tree

The command is designed to be rerun safely. Existing inline comment
blocks that already sit immediately above a generated anchor line are
treated as owned and are not stacked on subsequent runs.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

if __package__ in {None, ""}:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from docify.tools.python_docstring_synthesize import (  # noqa: E402
    _attach_parents,
    apply_google_docstring_to_class_node,
    apply_google_docstring_to_function_node,
    apply_module_google_docstring,
    repair_class_docstring_in_source,
    repair_function_google_docstring_in_source,
    repair_module_docstring_in_source,
)
from docify.tools.python_inline_explain import annotate_function_inline  # noqa: E402

EXCLUDED_DIRS = {
    "__pycache__",
    ".venv",
    ".tox",
    "node_modules",
    ".git",
    ".fydata",
    "generated",
    "imports",
    "reports",
    "docs",
}


@dataclass(frozen=True)
class CallableRef:
    """Reference to one callable that may need documentation work."""

    qualname: str
    lineno: int


@dataclass(frozen=True)
class FileUpdate:
    """Summary of the documentation changes applied to one file."""

    path: str
    module_docstring_added: bool
    docstrings_added: int
    docstrings_repaired: int
    inline_comment_passes: int


@dataclass(frozen=True)
class RunSummary:
    """Aggregate counters for one repo-wide documentation pass."""

    scanned_python_files: int
    changed_files: int
    module_docstrings_added: int
    docstrings_added: int
    docstrings_repaired: int
    inline_comment_passes: int


def _rel_posix(path: Path, repo_root: Path) -> str:
    """Return a repository-relative POSIX path.

    Args:
        path: Filesystem path to the file or directory being processed.
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _iter_python_files(root: Path, *, include_tests: bool) -> Iterable[Path]:
    """Yield documentable Python files below *root*.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        include_tests: Whether to enable this optional behavior.

    Returns:
        Iterable[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    # Process (dirpath, dirnames, filenames) one item at a time so _iter_python_files
    # applies the same rule across the full collection.
    for dirpath, dirnames, filenames in os.walk(root):
        # Build filesystem locations and shared state that the rest of
        # _iter_python_files reuses.
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        current_dir = Path(dirpath)
        rel_parts = current_dir.relative_to(root).parts if current_dir != root else ()
        # Branch on not include_tests and 'tests' in rel_parts so _iter_python_files
        # only continues along the matching state path.
        if not include_tests and "tests" in rel_parts:
            dirnames[:] = []
            continue
        # Process filename one item at a time so _iter_python_files applies the same
        # rule across the full collection.
        for filename in filenames:
            # Branch on not filename.endswith('.py') so _iter_python_files only
            # continues along the matching state path.
            if not filename.endswith(".py"):
                continue
            path = current_dir / filename
            rel_parts = path.relative_to(root).parts
            # Branch on not include_tests and 'tests' in rel_parts so _iter_python_files
            # only continues along the matching state path.
            if not include_tests and "tests" in rel_parts:
                continue
            yield path


def _has_docstring(node: ast.AST) -> bool:
    """Return whether *node* has a non-empty docstring.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    doc = ast.get_docstring(node, clean=False)
    return bool(doc and doc.strip())


def _callable_qualname(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return ``Class.method`` for methods and the bare name for functions.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    parts = [node.name]
    parent = getattr(node, "parent", None)
    while isinstance(parent, ast.ClassDef):
        parts.append(parent.name)
        parent = getattr(parent, "parent", None)
    return ".".join(reversed(parts))


def _body_without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Drop the leading docstring statement when present.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        body: Primary body used by this step.

    Returns:
        list[ast.stmt]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if body and isinstance(body[0], ast.Expr):
        value = getattr(body[0], "value", None)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return body[1:]
    return body


def _needs_inline_comments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether *node* is complex enough to deserve inline comments.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    body = _body_without_docstring(list(node.body))
    if len(body) >= 4:
        return True
    if any(
        isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith))
        for stmt in body
    ):
        return True
    if len(body) >= 2 and any(
        isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr))
        for stmt in body
    ):
        return True
    return False


def _collect_missing_doc_targets(
    source: str,
) -> tuple[bool, list[ast.ClassDef], list[ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Return missing module, class, and callable docstring targets.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.

    Returns:
        tuple[bool, list[ast.ClassDef], list[ast.FunctionDef | ast....:
            Collection produced from the parsed or
            accumulated input data.
    """
    tree = ast.parse(source)
    _attach_parents(tree)
    classes: list[ast.ClassDef] = []
    callables: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not _has_docstring(node):
            classes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _has_docstring(node):
            callables.append(node)
    classes.sort(key=lambda node: int(node.lineno), reverse=True)
    callables.sort(key=lambda node: int(node.lineno), reverse=True)
    return not _has_docstring(tree), classes, callables


def _repair_docstrings(source: str, *, rel_posix: str) -> tuple[str, int]:
    """Repair layout issues in existing docstrings and return the new
    source.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.

    Returns:
        tuple[str, int]:
            Collection produced from the parsed or
            accumulated input data.
    """
    repairs = 0
    tree = ast.parse(source)
    _attach_parents(tree)

    new_source, error = repair_module_docstring_in_source(
        source,
        tree,
        rel_posix=rel_posix,
    )
    if error:
        raise ValueError(error)
    if new_source != source:
        repairs += 1
        source = new_source

    tree = ast.parse(source)
    _attach_parents(tree)
    class_nodes = sorted(
        [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and _has_docstring(node)],
        key=lambda node: int(node.lineno),
        reverse=True,
    )
    for node in class_nodes:
        new_source, error = repair_class_docstring_in_source(source, node)
        if error:
            raise ValueError(error)
        if new_source != source:
            repairs += 1
            source = new_source

    tree = ast.parse(source)
    _attach_parents(tree)
    callable_nodes = sorted(
        [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _has_docstring(node)
        ],
        key=lambda node: int(node.lineno),
        reverse=True,
    )
    for node in callable_nodes:
        new_source, error = repair_function_google_docstring_in_source(source, node)
        if error:
            raise ValueError(error)
        if new_source != source:
            repairs += 1
            source = new_source

    return source, repairs


def _apply_missing_docstrings(source: str, *, rel_posix: str) -> tuple[str, bool, int]:
    """Insert missing module, class, and callable docstrings.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        rel_posix: Primary rel posix used by this step.

    Returns:
        tuple[str, bool, int]:
            Collection produced from the parsed or
            accumulated input data.
    """
    module_missing, class_nodes, callable_nodes = _collect_missing_doc_targets(source)
    module_added = False
    added = 0

    if module_missing:
        new_source, error = apply_module_google_docstring(source, rel_posix=rel_posix)
        if error:
            raise ValueError(error)
        if new_source != source:
            source = new_source
            module_added = True
            added += 1

    tree = ast.parse(source)
    _attach_parents(tree)
    callable_nodes = sorted(
        [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not _has_docstring(node)
        ],
        key=lambda node: int(node.lineno),
        reverse=True,
    )

    for node in callable_nodes:
        new_source, error = apply_google_docstring_to_function_node(source, node)
        if error:
            raise ValueError(error)
        if new_source != source:
            source = new_source
            added += 1

    tree = ast.parse(source)
    _attach_parents(tree)
    class_nodes = sorted(
        [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and not _has_docstring(node)],
        key=lambda node: int(node.lineno),
        reverse=True,
    )
    for node in class_nodes:
        new_source, error = apply_google_docstring_to_class_node(source, node)
        if error:
            raise ValueError(error)
        if new_source != source:
            source = new_source
            added += 1

    return source, module_added, added - int(module_added)


def _apply_inline_comments(source: str) -> tuple[str, int]:
    """Add grouped inline comments to longer functions and methods.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.

    Returns:
        tuple[str, int]:
            Collection produced from the parsed or
            accumulated input data.
    """
    tree = ast.parse(source)
    _attach_parents(tree)
    callables = sorted(
        [
            CallableRef(_callable_qualname(node), int(node.lineno))
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _needs_inline_comments(node)
        ],
        key=lambda item: item.lineno,
        reverse=True,
    )
    passes = 0
    for ref in callables:
        new_source = annotate_function_inline(source, ref.qualname, mode="dense")
        if new_source != source:
            source = new_source
            passes += 1
    return source, passes


def document_python_file(path: Path, *, repo_root: Path) -> FileUpdate | None:
    """Document one Python file and write it back when needed.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        FileUpdate | None:
            Value produced by this callable as ``FileUpdate
            | None``.
    """
    source = path.read_text(encoding="utf-8")
    rel_posix = _rel_posix(path, repo_root)

    source, module_added, docstrings_added = _apply_missing_docstrings(
        source,
        rel_posix=rel_posix,
    )
    source, docstrings_repaired = _repair_docstrings(
        source,
        rel_posix=rel_posix,
    )
    source, inline_passes = _apply_inline_comments(source)

    new_source = source
    old_source = path.read_text(encoding="utf-8")
    if new_source == old_source:
        return None

    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(new_source, encoding="utf-8", newline="\n")
    return FileUpdate(
        path=rel_posix,
        module_docstring_added=module_added,
        docstrings_added=docstrings_added,
        docstrings_repaired=docstrings_repaired,
        inline_comment_passes=inline_passes,
    )


def run_documentation_pass(
    *,
    repo_root: Path,
    root: Path,
    include_tests: bool,
) -> tuple[RunSummary, list[FileUpdate]]:
    """Run the repo-wide documentation pass and return a summary.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        root: Root directory used to resolve repository-local paths.
        include_tests: Whether to enable this optional behavior.

    Returns:
        tuple[RunSummary, list[FileUpdate]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    updates: list[FileUpdate] = []
    scanned = 0
    for path in _iter_python_files(root, include_tests=include_tests):
        scanned += 1
        update = document_python_file(path, repo_root=repo_root)
        if update is not None:
            updates.append(update)

    summary = RunSummary(
        scanned_python_files=scanned,
        changed_files=len(updates),
        module_docstrings_added=sum(int(item.module_docstring_added) for item in updates),
        docstrings_added=sum(item.docstrings_added for item in updates),
        docstrings_repaired=sum(item.docstrings_repaired for item in updates),
        inline_comment_passes=sum(item.inline_comment_passes for item in updates),
    )
    return summary, updates


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for repo-wide Python documentation runs.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    parser = argparse.ArgumentParser(
        description="Document a Python tree with Docify-generated docstrings and comments."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = args.repo_root.expanduser().resolve()
    root = args.root.expanduser()
    root = root if root.is_absolute() else (repo_root / root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    if not args.apply:
        print("--apply is required for repo-wide documentation runs.", file=sys.stderr)
        return 2

    summary, updates = run_documentation_pass(
        repo_root=repo_root,
        root=root,
        include_tests=args.include_tests,
    )

    payload = {
        "repo_root": str(repo_root),
        "root": str(root),
        "include_tests": args.include_tests,
        "summary": asdict(summary),
        "updates": [asdict(item) for item in updates],
    }
    if args.json or args.out:
        text = json.dumps(payload, indent=2) + "\n"
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    else:
        print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
