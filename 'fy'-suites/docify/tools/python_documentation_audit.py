#!/usr/bin/env python3
"""
Docify hub CLI — static audit for Python documentation hygiene across
the monorepo.

Scans selected source trees with the ``ast`` module and reports module,
class, and function/method definitions that lack a usable docstring.
Intended for humans and coding agents planning incremental documentation
work without changing runtime behavior.

Repository policy: user-facing narrative may vary by layer, but
maintainer facing code comments and docstrings in committed Python stay
English; this tool emits English messages only.

Examples:

# Preferred (editable install): same flags via the hub CLI
    python -m docify.tools audit --json --out doc_audit.json

# Default scan: backend, world-engine, ai_stack, frontend,
administration-tool, # story_runtime_core, 'fy'-suites/despaghettify,
postmanify, tools/mcp_server, # 'fy'-suites/docify (self-governance
slice included) python
"./'fy'-suites/docify/tools/python_documentation_audit.py"

# Machine-readable backlog for an agent python
"./'fy'-suites/docify/tools/python_documentation_audit.py" --json --out
doc_audit.json

# Include tests and private ``_`` symbols python
"./'fy'-suites/docify/tools/python_documentation_audit.py"
--include-tests --include-private

# Append Ruff issues when ``ruff`` is on PATH (optional) python
"./'fy'-suites/docify/tools/python_documentation_audit.py" --with-ruff

# Google-style layout hints on existing docstrings (Args/Returns/width)
python "./'fy'-suites/docify/tools/python_documentation_audit.py" --root
path/to/package --google-docstring-audit --exit-zero
"""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from fy_platform.core.artifact_envelope import build_envelope, write_envelope
from fy_platform.core.manifest import load_manifest, roots_for_suite
from fy_platform.core.project_resolver import resolve_project_root

SUITE_VERSION = "0.1.0"


@dataclass(frozen=True)
class Finding:
    """Single documentation gap surfaced for one AST node."""

    path: str
    line: int
    kind: str
    name: str
    code: str


# Default docstring scan: all major Python systems (application + entrypoints).
# Use ``--include-tests`` to add ``**/tests/**`` trees. Subpaths are avoided so each
# file is visited once (no overlapping roots).
DEFAULT_RELATIVE_ROOTS: tuple[str, ...] = (
    "backend",
    "world-engine",
    "ai_stack",
    "frontend",
    "administration-tool",
    "story_runtime_core",
    "'fy'-suites/despaghettify",
    "'fy'-suites/postmanify",
    "'fy'-suites/docify",
    "'fy'-suites/contractify",
    "tools/mcp_server",
)

DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "**/migrations/**",
    "**/__pycache__/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/site-packages/**",
    "**/.tox/**",
    "**/.eggs/**",
    # World Engine may ship an embedded CPython layout under ``source/`` (not project code).
    "world-engine/source/**",
)


def _repo_root() -> Path:
    """Return repository root using shared resolver with
    backward-compatible marker.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return resolve_project_root(start=Path(__file__), marker_text=None)


def _posix_relative(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` using forward slashes.

    Args:
        path: Filesystem path to the file or directory being processed.
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return path.resolve().relative_to(root).as_posix()


def _matches_globs(rel_posix: str, patterns: Sequence[str]) -> bool:
    """Matches globs.

    Args:
        rel_posix: Primary rel posix used by this step.
        patterns: Primary patterns used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return any(fnmatch.fnmatch(rel_posix, pat) for pat in patterns)


def _is_test_path(rel_posix: str) -> bool:
    """Return whether test path.

    Args:
        rel_posix: Primary rel posix used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    parts = rel_posix.split("/")
    return "tests" in parts


def _is_private_name(name: str) -> bool:
    """Return whether private name.

    Args:
        name: Primary name used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def iter_python_files(
    roots: Sequence[Path],
    *,
    repo_root: Path,
    exclude_globs: Sequence[str],
    include_tests: bool,
) -> Iterator[Path]:
    """Yield ``.py`` files under ``roots`` respecting filters.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        roots: Primary roots used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        exclude_globs: Primary exclude globs used by this step.
        include_tests: Whether to enable this optional behavior.

    Returns:
        Iterator[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune obvious junk early to avoid deep walks.
            pruned: list[str] = []
            for name in dirnames:
                if name in {"__pycache__", ".venv", "node_modules", ".git"}:
                    pruned.append(name)
            for name in pruned:
                if name in dirnames:
                    dirnames.remove(name)

            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = Path(dirpath) / filename
                rel = _posix_relative(path, repo_root)
                if _matches_globs(rel, exclude_globs):
                    continue
                if not include_tests and _is_test_path(rel):
                    continue
                yield path


class _DocstringAuditor(ast.NodeVisitor):
    """Collect missing or whitespace-only docstrings for public API surfaces."""

    def __init__(
        self,
        *,
        rel_path: str,
        include_private: bool,
    ) -> None:
        """Configure the visitor for one module path.

        Args:
            rel_path: Filesystem path to the file or directory being
                processed.
            include_private: Whether to enable this optional behavior.
        """
        self._rel_path = rel_path
        self._include_private = include_private
        self.findings: list[Finding] = []
        self._function_depth = 0

    def visit_Module(self, node: ast.Module) -> None:
        """Record missing module docstrings and recurse.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        doc = ast.get_docstring(node, clean=False)
        if doc is None or not doc.strip():
            self.findings.append(
                Finding(
                    path=self._rel_path,
                    line=1,
                    kind="module",
                    name="<module>",
                    code="MISSING_OR_EMPTY_DOCSTRING",
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Record missing class docstrings for in-scope classes and
        recurse.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        if not self._include_private and _is_private_name(node.name):
            self.generic_visit(node)
            return
        doc = ast.get_docstring(node, clean=False)
        if doc is None or not doc.strip():
            self.findings.append(
                Finding(
                    path=self._rel_path,
                    line=int(node.lineno),
                    kind="class",
                    name=node.name,
                    code="MISSING_OR_EMPTY_DOCSTRING",
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Inspect top-level functions and class members for usable
        docstrings.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        self._visit_functionlike(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Async variant of ``visit_FunctionDef``.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        self._visit_functionlike(node)

    def _visit_functionlike(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Visit functionlike.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        if self._function_depth > 0:
            # Skip nested helpers; focus backlog on module and class members.
            self.generic_visit(node)
            return
        parent = getattr(node, "parent", None)
        if (
            isinstance(parent, ast.ClassDef)
            and parent.name.startswith("_")
            and node.name.startswith("visit_")
        ):
            # Private ``ast.NodeVisitor`` helpers: docstrings are optional noise here.
            self._function_depth += 1
            self.generic_visit(node)
            self._function_depth -= 1
            return
        if not self._include_private and _is_private_name(node.name):
            self.generic_visit(node)
            return
        doc = ast.get_docstring(node, clean=False)
        if doc is None or not doc.strip():
            kind = "function" if isinstance(parent, ast.Module) else "method"
            self.findings.append(
                Finding(
                    path=self._rel_path,
                    line=int(node.lineno),
                    kind=kind,
                    name=node.name,
                    code="MISSING_OR_EMPTY_DOCSTRING",
                )
            )
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1


def _attach_parents(node: ast.AST) -> None:
    """Populate ``parent`` links for AST nodes (``ast`` does not set them).

    The implementation iterates over intermediate items before it
    returns.

    Args:
        node: Parsed AST object being inspected or transformed.
    """
    for child in ast.iter_child_nodes(node):
        setattr(child, "parent", node)  # noqa: B010
        _attach_parents(child)


def audit_file(
    path: Path,
    *,
    rel_path: str,
    include_private: bool,
    google_docstring_audit: bool = False,
    docstring_max_line: int = 72,
) -> list[Finding]:
    """Parse *path* and return documentation findings.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        rel_path: Filesystem path to the file or directory being
            processed.
        include_private: Whether to enable this optional behavior.
        google_docstring_audit: Whether to enable this optional
            behavior.
        docstring_max_line: 1-based source line number used by the audit
            or edit step.

    Returns:
        list[Finding]:
            Collection produced from the parsed or
            accumulated input data.
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    _attach_parents(tree)
    visitor = _DocstringAuditor(rel_path=rel_path, include_private=include_private)
    visitor.visit(tree)
    out = list(visitor.findings)
    if google_docstring_audit:
        gvis = _GoogleStyleDocstringAuditor(
            rel_path=rel_path,
            include_private=include_private,
            max_line=docstring_max_line,
        )
        gvis.visit(tree)
        out.extend(gvis.findings)
    return out


class _GoogleStyleDocstringAuditor(ast.NodeVisitor):
    """Optional checks: PEP 8 docstring width, Google ``Args`` / ``Returns``
    sections.
    """

    def __init__(self, *, rel_path: str, include_private: bool, max_line: int) -> None:
        """Configure Google-style layout checks for one module path.

        Args:
            rel_path: Filesystem path to the file or directory being
                processed.
            include_private: Whether to enable this optional behavior.
            max_line: 1-based source line number used by the audit or
                edit step.
        """
        self._rel_path = rel_path
        self._include_private = include_private
        self.findings: list[Finding] = []
        self._function_depth = 0
        self._max_line = max_line

    def visit_Module(self, node: ast.Module) -> None:
        """Check module docstring width when present.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        doc = ast.get_docstring(node, clean=False)
        if doc and doc.strip():
            self._check_line_lengths(kind="module", name="<module>", line=1, doc=doc)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class docstring width when present.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        if not self._include_private and _is_private_name(node.name):
            self.generic_visit(node)
            return
        doc = ast.get_docstring(node, clean=False)
        if doc and doc.strip():
            self._check_line_lengths(kind="class", name=node.name, line=int(node.lineno), doc=doc)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Inspect callables for Google layout hints.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        self._visit_functionlike(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Async variant of ``visit_FunctionDef``.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        self._visit_functionlike(node)

    def _visit_functionlike(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Visit functionlike.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
        """
        if self._function_depth > 0:
            self.generic_visit(node)
            return
        parent = getattr(node, "parent", None)
        if (
            isinstance(parent, ast.ClassDef)
            and parent.name.startswith("_")
            and node.name.startswith("visit_")
        ):
            self._function_depth += 1
            self.generic_visit(node)
            self._function_depth -= 1
            return
        if not self._include_private and _is_private_name(node.name):
            self.generic_visit(node)
            return
        doc = ast.get_docstring(node, clean=False)
        if not doc or not doc.strip():
            self._function_depth += 1
            self.generic_visit(node)
            self._function_depth -= 1
            return

        kind = "function" if isinstance(parent, ast.Module) else "method"
        self._check_line_lengths(kind=kind, name=node.name, line=int(node.lineno), doc=doc)
        self._check_google_sections(node, kind=kind, doc=doc)

        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def _check_line_lengths(
        self,
        *,
        kind: str,
        name: str,
        line: int,
        doc: str,
    ) -> None:
        """Check line lengths.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            kind: Primary kind used by this step.
            name: Primary name used by this step.
            line: 1-based source line number used by the audit or edit
                step.
            doc: Text content to inspect or rewrite.
        """
        for ln in doc.splitlines():
            if len(ln) > self._max_line:
                self.findings.append(
                    Finding(
                        path=self._rel_path,
                        line=line,
                        kind=kind,
                        name=name,
                        code="DOCSTRING_LINE_OVER_LONG",
                    )
                )
                return

    def _check_google_sections(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, kind: str, doc: str) -> None:
        """Check google sections.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            node: Parsed AST object being inspected or transformed.
            kind: Primary kind used by this step.
            doc: Text content to inspect or rewrite.
        """
        if not re.search(r"(?m)^\s*Args:\s*$", doc):
            args = [*node.args.posonlyargs, *node.args.args]
            if kind == "method" and args and args[0].arg in ("self", "cls"):
                args = args[1:]
            if args or node.args.vararg or node.args.kwonlyargs or node.args.kwarg:
                self.findings.append(
                    Finding(
                        path=self._rel_path,
                        line=int(node.lineno),
                        kind=kind,
                        name=node.name,
                        code="DOCSTRING_MISSING_ARGS_SECTION",
                    )
                )

        ret = node.returns
        needs_returns = ret is not None and not (
            isinstance(ret, ast.Constant) and ret.value is None
        )
        if needs_returns and not re.search(r"(?m)^\s*Returns:\s*$", doc):
            self.findings.append(
                Finding(
                    path=self._rel_path,
                    line=int(node.lineno),
                    kind=kind,
                    name=node.name,
                    code="DOCSTRING_MISSING_RETURNS_SECTION",
                )
            )
            return

        if needs_returns and re.search(r"(?m)^\s*Returns:\s*$", doc):
            after = re.split(r"(?m)^\s*Returns:\s*$", doc, maxsplit=1)[-1]
            tail_lines = [ln for ln in after.splitlines() if ln.strip()]
            type_line = tail_lines[0] if tail_lines else ""
            type_line_ok = bool(
                re.match(r"^\s*[A-Za-z_][\w\[\].<> ,|]*:\s*$", type_line)
            )
            if not type_line_ok:
                self.findings.append(
                    Finding(
                        path=self._rel_path,
                        line=int(node.lineno),
                        kind=kind,
                        name=node.name,
                        code="DOCSTRING_RETURNS_WITHOUT_TYPE_LINE",
                    )
                )


def _parse_roots(repo_root: Path, raw: Sequence[str] | None) -> list[Path]:
    """Parse roots.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        raw: Primary raw used by this step.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    if raw:
        resolved: list[Path] = []
        for item in raw:
            path = Path(item)
            resolved.append(path.resolve() if path.is_absolute() else (repo_root / path).resolve())
        return resolved
    manifest, _warnings = load_manifest(repo_root)
    manifest_roots = roots_for_suite(manifest=manifest, suite_name="docify")
    selected = tuple(manifest_roots) if manifest_roots else DEFAULT_RELATIVE_ROOTS
    return [(repo_root / rel).resolve() for rel in selected]


def _maybe_run_ruff(roots: Sequence[Path]) -> tuple[int, str]:
    """Run ``ruff check`` across *roots* when available; return exit code
    and output.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        roots: Primary roots used by this step.

    Returns:
        tuple[int, str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    try:
        proc = subprocess.run(
            ["ruff", "check", *[str(r) for r in roots if r.is_dir()]],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return 127, "ruff not found on PATH; install ruff or omit --with-ruff"
    out = (proc.stdout or "") + (proc.stderr or "")
    return int(proc.returncode), out


def _group_by_path(findings: Iterable[Finding]) -> dict[str, list[Finding]]:
    """Group by path.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        findings: Primary findings used by this step.

    Returns:
        dict[str, list[Finding]]:
            Structured payload describing the outcome of the
            operation.
    """
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for item in findings:
        grouped[item.path].append(item)
    return dict(grouped)


def _emit_text(findings: list[Finding], *, max_files: int | None) -> None:
    """Emit text.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        findings: Primary findings used by this step.
        max_files: Primary max files used by this step.
    """
    grouped = _group_by_path(findings)
    paths = sorted(grouped)
    if max_files is not None:
        paths = paths[: max(0, max_files)]
    for path in paths:
        print(path)
        for finding in sorted(grouped[path], key=lambda f: (f.line, f.name)):
            print(f"  L{finding.line:5d}  {finding.kind:8s}  {finding.name}  ({finding.code})")
        print()


def _emit_json(
    findings: list[Finding],
    *,
    repo_root: Path,
    roots: Sequence[Path],
    parse_errors: Sequence[str],
    ruff_exit: int | None,
    ruff_output: str | None,
) -> str:
    """Emit json.

    Args:
        findings: Primary findings used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        roots: Primary roots used by this step.
        parse_errors: Primary parse errors used by this step.
        ruff_exit: Primary ruff exit used by this step.
        ruff_output: Primary ruff output used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    payload = {
        "repo_root": str(repo_root),
        "roots": [str(r) for r in roots],
        "summary": {
            "findings": len(findings),
            "files_with_findings": len({f.path for f in findings}),
            "parse_errors": len(parse_errors),
        },
        "parse_errors": list(parse_errors),
        "findings": [asdict(f) for f in findings],
        "ruff": None
        if ruff_exit is None
        else {
            "exit_code": ruff_exit,
            "output_tail": (ruff_output or "")[-8000:],
        },
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry for the documentation audit (also reachable as ``docify
    audit``).

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        default=None,
        help="Relative or absolute directory to scan (repeatable). Defaults to curated monorepo packages.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to two levels above this script).",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        dest="exclude_globs",
        default=[],
        help="fnmatch pattern relative to repo root (repeatable).",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include paths whose components contain a ``tests`` segment.",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include classes and callables whose names start with a single underscore.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human text.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON output to this file (implies --json).",
    )
    parser.add_argument(
        "--envelope-out",
        type=Path,
        default=None,
        help="Optional path to write shared versioned envelope JSON.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit number of files listed in text mode (newest paths not guaranteed).",
    )
    parser.add_argument(
        "--with-ruff",
        action="store_true",
        help="Append ``ruff check`` output when the ``ruff`` executable is available.",
    )
    parser.add_argument(
        "--google-docstring-audit",
        action="store_true",
        help=(
            "Also flag docstrings that violate Google layout hints: ``Args`` / ``Returns`` "
            "sections when parameters or return annotations warrant them, a ``Type:`` style "
            "line after ``Returns:``, and docstring body lines longer than --docstring-max-line."
        ),
    )
    parser.add_argument(
        "--docstring-max-line",
        type=int,
        default=72,
        help="Maximum physical line length inside docstring bodies for --google-docstring-audit.",
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Always exit with status 0 unless source files fail to parse.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = (args.repo_root or _repo_root()).resolve()
    manifest, _manifest_warnings = load_manifest(repo_root)
    roots = _parse_roots(repo_root, args.roots)
    exclude_globs = tuple(dict.fromkeys([*DEFAULT_EXCLUDE_GLOBS, *args.exclude_globs]))

    findings: list[Finding] = []
    parse_errors: list[str] = []

    for path in iter_python_files(
        roots,
        repo_root=repo_root,
        exclude_globs=exclude_globs,
        include_tests=bool(args.include_tests),
    ):
        rel = _posix_relative(path, repo_root)
        try:
            findings.extend(
                audit_file(
                    path,
                    rel_path=rel,
                    include_private=bool(args.include_private),
                    google_docstring_audit=bool(args.google_docstring_audit),
                    docstring_max_line=int(args.docstring_max_line),
                )
            )
        except (SyntaxError, UnicodeError) as exc:
            parse_errors.append(f"{rel}: {exc.__class__.__name__}: {exc}")

    ruff_exit: int | None = None
    ruff_output: str | None = None
    if args.with_ruff:
        ruff_exit, ruff_output = _maybe_run_ruff(roots)

    if args.out is not None:
        args.json = True

    if args.json:
        text = _emit_json(
            findings,
            repo_root=repo_root,
            roots=roots,
            parse_errors=parse_errors,
            ruff_exit=ruff_exit,
            ruff_output=ruff_output,
        )
        if args.out is not None:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        if args.envelope_out is not None:
            payload = json.loads(text)
            deprecations: list[dict[str, str]] = []
            if manifest is None:
                msg = "No fy-manifest.yaml detected; Docify is running in legacy fallback mode."
                print(f"DEPRECATION: {msg}", file=sys.stderr)
                deprecations.append(
                    {
                        "id": "DOCIFY-LEGACY-FALLBACK-001",
                        "message": msg,
                        "replacement": "Run fy-platform bootstrap and configure suites.docify.roots",
                        "removal_target": "wave-2",
                    }
                )
            env = build_envelope(
                suite="docify",
                suite_version=SUITE_VERSION,
                payload=payload,
                manifest_ref="fy-manifest.yaml",
                deprecations=deprecations,
                findings=payload.get("findings", []),
                evidence=[{"kind": "parse_error", "source_path": pe, "deterministic": True} for pe in payload.get("parse_errors", [])],
                stats=payload.get("summary", {}),
            )
            out_path = args.envelope_out
            if not out_path.is_absolute():
                out_path = repo_root / out_path
            write_envelope(out_path, env)
            if deprecations:
                dep_path = out_path.with_suffix(out_path.suffix + ".deprecations.md")
                lines = ["# Deprecations", ""]
                for item in deprecations:
                    lines.append(f"- `{item['id']}`: {item['message']}")
                    lines.append(f"  - replacement: `{item['replacement']}`")
                    lines.append(f"  - removal_target: `{item['removal_target']}`")
                # Write the human-readable companion text so reviewers can inspect the
                # result without opening raw structured data.
                dep_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        print(f"Repo root: {repo_root}")
        print(f"Roots: {', '.join(_posix_relative(p, repo_root) for p in roots)}")
        print(f"Findings: {len(findings)} across {len({f.path for f in findings})} files")
        if parse_errors:
            print(f"Parse errors: {len(parse_errors)}")
            for line in parse_errors[:20]:
                print(f"  {line}")
            if len(parse_errors) > 20:
                print("  ...")
        if ruff_exit is not None:
            print(f"Ruff exit code: {ruff_exit}")
            if ruff_output:
                print(ruff_output.rstrip()[:4000])
        print()
        _emit_text(findings, max_files=args.max_files)

    # Non-zero exit when backlog exists or parse errors occurred (CI-friendly).
    if parse_errors:
        return 2
    if args.exit_zero:
        return 0
    if findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
