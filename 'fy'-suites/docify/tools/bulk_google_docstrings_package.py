#!/usr/bin/env python3
"""
Walk a Python package and apply draft Google-style module/class/function
docstrings.

Edits one symbol per re-parse (bottom-up by ``lineno``) so line numbers
stay valid. Skips nested functions and methods defined inside another
function body.

Run from the repository root, for example::

python "./'fy'-suites/docify/tools/bulk_google_docstrings_package.py"
--package-root ai_stack --dry-run
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
# Same convention as ``python_docstring_synthesize.py``: repo root is three levels
# above this *file* (``tools/`` → ``docify/`` → ``'fy'-suites/`` → repo).
_REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[3]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import python_docstring_synthesize as pds  # noqa: E402


def _callable_missing_doc(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    """Callable missing doc.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    # Branch on not node.body so _callable_missing_doc only continues along the matching
    # state path.
    if not node.body:
        return False
    stmt0 = node.body[0]
    # Branch on isinstance(stmt0, ast.Expr) and isinstance(st... so
    # _callable_missing_doc only continues along the matching state path.
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        return not stmt0.value.value.strip()
    return True


def _outside_nested_function(node: ast.AST) -> bool:
    """Outside nested function.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        cur = getattr(cur, "parent", None)
    return True


def _iter_py_files(package_root: Path) -> list[Path]:
    """Yield py files.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        package_root: Root directory used to resolve repository-local
            paths.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    out: list[Path] = []
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            rel = path.relative_to(package_root)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == "tests":
            continue
        out.append(path)
    return out


def _module_needs_doc(tree: ast.Module) -> bool:
    """Module needs doc.

    Args:
        tree: Parsed AST object being inspected or transformed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    doc = ast.get_docstring(tree, clean=False)
    return doc is None or not doc.strip()


def _pick_next_target(
    tree: ast.Module,
) -> tuple[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] | None:
    """Pick next target.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        tree: Parsed AST object being inspected or transformed.

    Returns:
        tuple[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.Cla...:
            Collection produced from the parsed or
            accumulated input data.
    """
    candidates: list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _callable_missing_doc(node) and _outside_nested_function(node):
                candidates.append(node)
        elif isinstance(node, ast.ClassDef):
            if _callable_missing_doc(node):
                candidates.append(node)
    if not candidates:
        return None
    best = max(candidates, key=lambda n: n.lineno or 0)
    kind = "class" if isinstance(best, ast.ClassDef) else "function"
    return kind, best


def process_file(
    path: Path,
    *,
    repo_root: Path,
    dry_run: bool,
) -> tuple[int, str | None]:
    """Return (edit_count, error_message).

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        path: Filesystem path to the file or directory being processed.
        repo_root: Root directory used to resolve repository-local
            paths.
        dry_run: Whether to enable this optional behavior.

    Returns:
        tuple[int, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    try:
        initial = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return 0, f"read: {exc}"

    source = initial
    edits = 0
    rel_posix = path.relative_to(repo_root).as_posix()
    guard = 0

    while True:
        guard += 1
        if guard > 8000:
            return edits, "iteration guard exceeded (possible apply no-op loop)"

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return edits, f"parse: {exc}"

        pds._attach_parents(tree)

        if _module_needs_doc(tree):
            new_src, err = pds.apply_module_google_docstring(source, rel_posix=rel_posix)
            if err:
                return edits, f"module docstring: {err}"
            if new_src == source:
                return edits, "module docstring needed but apply produced no change (stuck)"
            edits += 1
            source = new_src
            continue

        picked = _pick_next_target(tree)
        if picked is None:
            break
        kind, node = picked
        if kind == "class":
            new_src, err = pds.apply_google_docstring_to_class_node(source, node)
        else:
            new_src, err = pds.apply_google_docstring_to_function_node(source, node)
        if err:
            return edits, f"{kind} {getattr(node, 'name', '?')!r}: {err}"
        if new_src is None or new_src == source:
            break
        edits += 1
        source = new_src

    if not dry_run and source != initial:
        path.write_text(source, encoding="utf-8", newline="\n")

    return edits, None


def main() -> int:
    """Run the command-line entry point.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path("ai_stack"),
        help="Directory to scan (default: ai_stack)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for relative paths in module summaries (default: inferred)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stop after the first would-be edit per file (no writes)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N files (0 = no limit)",
    )
    args = parser.parse_args()
    repo_root = (args.repo_root or _REPO_ROOT_DEFAULT).resolve()
    pkg = (repo_root / args.package_root).resolve()
    if not pkg.is_dir():
        print(f"package root not found: {pkg}", file=sys.stderr)
        return 2

    paths = _iter_py_files(pkg)
    if args.limit:
        paths = paths[: args.limit]

    total_edits = 0
    errors: list[tuple[str, str]] = []
    for i, path in enumerate(paths):
        edits, err = process_file(path, repo_root=repo_root, dry_run=args.dry_run)
        total_edits += edits
        if err:
            errors.append((str(path.relative_to(repo_root)), err))
        if (i + 1) % 25 == 0:
            print(f"... {i + 1}/{len(paths)} files", file=sys.stderr)

    print(f"files: {len(paths)}  edits: {total_edits}  dry_run: {args.dry_run}")
    for rel, msg in errors[:50]:
        print(f"ERROR {rel}: {msg}", file=sys.stderr)
    if len(errors) > 50:
        print(f"... {len(errors) - 50} more errors", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
