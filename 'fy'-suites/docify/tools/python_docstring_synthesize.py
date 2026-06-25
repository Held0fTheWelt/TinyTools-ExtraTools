#!/usr/bin/env python3
"""Synthesize Google-style docstrings and PEP 8 inline comments.

This module powers Docify's Python documentation path. It can generate
or repair function, class, and module docstrings, and it can also insert
sparse inline comments for workflow-heavy functions.

Use ``python_documentation_audit.py`` for tree-wide validation after a
batch run.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

# PEP 8: prefer 79-char lines for code; block comments often use a shorter flow
# width for readability (matching common docstring guidance).
_COMMENT_FLOW_WIDTH = 72
# Docstring narrative width (PEP 257 recommends wrapping long docstring lines).
_DOCSTRING_FLOW_WIDTH = 72
# Matches ``python_documentation_audit.py`` Google docstring width checks.
_GOOGLE_DOCSTRING_MAX_LINE = 72


def reflow_plain_docstring_paragraphs(doc: str, *, width: int = _GOOGLE_DOCSTRING_MAX_LINE) -> str:
    """Reflow *doc* paragraphs so soft-wrapped lines stay within *width*
    (best effort).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        doc: Text content to inspect or rewrite.
        width: Primary width used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    doc = doc.strip()
    # Branch on not doc so reflow_plain_docstring_paragraphs only continues along the
    # matching state path.
    if not doc:
        return doc
    paras = doc.split("\n\n")
    new_paras: list[str] = []
    # Process raw one item at a time so reflow_plain_docstring_paragraphs applies the
    # same rule across the full collection.
    for raw in paras:
        lines = [ln.rstrip() for ln in raw.splitlines()]
        nonempty = [ln for ln in lines if ln.strip()]
        # Branch on not nonempty so reflow_plain_docstring_paragraphs only continues
        # along the matching state path.
        if not nonempty:
            continue
        # Branch on all((len(ln) <= width for ln in lines)) so
        # reflow_plain_docstring_paragraphs only continues along the matching state
        # path.
        if all(len(ln) <= width for ln in lines):
            new_paras.append("\n".join(lines).strip())
            continue
        flat = " ".join(ln.strip() for ln in nonempty)
        wrapped = textwrap.wrap(
            flat,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        new_paras.append("\n".join(wrapped) if wrapped else flat)
    return "\n\n".join(new_paras)

def _docstring_reflow_width(content_indent: str = "") -> int:
    """Return the maximum inner docstring width for the current indent.

    Args:
        content_indent: Leading whitespace used for continued docstring
            lines in the source file.

    Returns:
        int:
            Maximum line width that keeps the stored literal inside the
            audit boundary.
    """
    return max(16, _GOOGLE_DOCSTRING_MAX_LINE - len(content_indent))


def _docstring_looks_generated_or_noisy(doc: str) -> bool:
    """Return whether *doc* still looks like placeholder-heavy generated text.

    Args:
        doc: Text content to inspect or rewrite.

    Returns:
        bool:
            Boolean outcome for the requested condition check.
    """
    lowered = " ".join(doc.split()).lower()
    bad_markers = (
        "meaning follows the type and call sites",
        "group state and helpers for",
        "parameters ----------",
        "notes -----",
        "empty docstring",
        "input value for",
    )
    return any(marker in lowered for marker in bad_markers)



def _google_audit_missing_args_section(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    doc: str,
) -> bool:
    """Google audit missing args section.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.
        doc: Text content to inspect or rewrite.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if re.search(r"(?m)^\s*Args:\s*$", doc):
        return False
    args = [*node.args.posonlyargs, *node.args.args]
    if _callable_kind(node) == "method" and args and args[0].arg in ("self", "cls"):
        args = args[1:]
    return bool(args or node.args.vararg or node.args.kwonlyargs or node.args.kwarg)


def _google_audit_missing_returns_section(node: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> bool:
    """Google audit missing returns section.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.
        doc: Text content to inspect or rewrite.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    ret = node.returns
    needs = ret is not None and not (isinstance(ret, ast.Constant) and ret.value is None)
    if not needs:
        return False
    return not re.search(r"(?m)^\s*Returns:\s*$", doc)


def _google_returns_type_line_invalid(node: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> bool:
    """True when ``Returns:`` exists but the first non-empty tail line
    fails the audit regex.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.
        doc: Text content to inspect or rewrite.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if not _needs_returns_section(node.returns):
        return False
    if not re.search(r"(?m)^\s*Returns:\s*$", doc):
        return False
    after = re.split(r"(?m)^\s*Returns:\s*$", doc, maxsplit=1)[-1]
    tail_lines = [ln for ln in after.splitlines() if ln.strip()]
    type_line = tail_lines[0] if tail_lines else ""
    return not bool(re.match(r"^\s*[A-Za-z_][\w\[\].<> ,|]*:\s*$", type_line))


def _google_audit_doc_has_long_line(doc: str, *, width: int = _GOOGLE_DOCSTRING_MAX_LINE) -> bool:
    """Google audit doc has long line.

    Args:
        doc: Text content to inspect or rewrite.
        width: Primary width used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return any(len(line) > width for line in doc.splitlines())


def _first_summary_paragraph_for_reuse(doc_clean: str) -> str | None:
    """First summary paragraph for reuse.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        doc_clean: Primary doc clean used by this step.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    head = re.split(r"(?m)^Args:\s*$", doc_clean, maxsplit=1)[0].strip()
    head = re.split(r"(?m)^Returns:\s*$", head, maxsplit=1)[0].strip()
    if not head:
        return None
    first = head.split("\n\n")[0].strip()
    return first or None


def format_function_docstring_from_dedented_body(
    dedent_body: str,
    content_indent: str,
) -> str:
    """Build a triple-quoted function docstring statement from
    already-dedented body text.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        dedent_body: Primary dedent body used by this step.
        content_indent: Primary content indent used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = dedent_body.rstrip().split("\n")
    if not lines:
        inner_prefixed = [content_indent]
    else:
        inner_prefixed = [f"{content_indent}{ln}" for ln in lines]
    first_text = inner_prefixed[0][len(content_indent) :]
    parts: list[str] = [f'{content_indent}"""{first_text}']
    for ln in inner_prefixed[1:]:
        parts.append("\n" + ln)
    parts.append(f'\n{content_indent}"""\n')
    return "".join(parts)


def format_top_module_docstring_block(inner: str) -> str:
    """Format a module-level docstring (column 0) with lines wrapped inside
    the literal.

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
    inner = inner.rstrip("\n")
    lines = inner.splitlines() or [""]
    if len(lines) == 1 and len(lines[0]) + 3 <= _GOOGLE_DOCSTRING_MAX_LINE:
        return f'"""{lines[0]}\n\n"""\n'
    parts = ['"""\n']
    for ln in lines:
        parts.append(ln + "\n")
    parts.append('"""\n')
    return "".join(parts)


def _stmt_span(node: ast.stmt) -> tuple[int, int]:
    """Return (lineno, end_lineno) with sensible fallbacks.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        tuple[int, int]:
            Collection produced from the parsed or
            accumulated input data.
    """
    start = getattr(node, "lineno", 1) or 1
    end = getattr(node, "end_lineno", None) or start
    return start, end


def _intersects(line_start: int, line_end: int, sel_start: int, sel_end: int) -> bool:
    """Intersects the requested operation.

    Args:
        line_start: Primary line start used by this step.
        line_end: Primary line end used by this step.
        sel_start: Primary sel start used by this step.
        sel_end: Primary sel end used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return not (line_end < sel_start or line_start > sel_end)


def _function_spanning_range(
    tree: ast.Module,
    start: int,
    end: int,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the innermost function whose body span contains [start, end].

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        tree: Parsed AST object being inspected or transformed.
        start: Primary start used by this step.
        end: Primary end used by this step.

    Returns:
        ast.FunctionDef | ast.AsyncFunctionDef | None:
            Value produced by this callable as
            ``ast.FunctionDef | ast.AsyncFunctionDef |
            None``.
    """
    candidates: list[tuple[int, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    class V(ast.NodeVisitor):
        """Coordinate v behavior.
        """
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
            """Visit function def nodes during AST traversal.

            Args:
                node: Parsed AST object being inspected or transformed.
            """
            self._maybe_add(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
            """Visit async function def nodes during AST traversal.

            Args:
                node: Parsed AST object being inspected or transformed.
            """
            self._maybe_add(node)

        def _maybe_add(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            """Maybe add.

            Control flow branches on the parsed state rather than
            relying on one linear path.

            Args:
                node: Parsed AST object being inspected or transformed.
            """
            s, e = _stmt_span(node)
            if s <= start and e >= end:
                span = e - s
                candidates.append((span, node))
            self.generic_visit(node)

    V().visit(tree)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _indent_for_line(lines: list[str], lineno: int) -> str:
    """Indent for line.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        lines: Primary lines used by this step.
        lineno: 1-based source line number used by the audit or edit
            step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    idx = lineno - 1
    if 0 <= idx < len(lines):
        raw = lines[idx]
        return raw[: len(raw) - len(raw.lstrip())]
    return ""


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


def _find_function(
    tree: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the first ``FunctionDef`` / ``AsyncFunctionDef`` with *name*.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        tree: Parsed AST object being inspected or transformed.
        name: Primary name used by this step.

    Returns:
        ast.FunctionDef | ast.AsyncFunctionDef | None:
            Value produced by this callable as
            ``ast.FunctionDef | ast.AsyncFunctionDef |
            None``.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _callable_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Callable kind.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    parent = getattr(node, "parent", None)
    return "method" if isinstance(parent, ast.ClassDef) else "function"


def _unparse(node: ast.AST | None) -> str | None:
    """Unparse the requested operation.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except AttributeError:
        return None


def _return_type_label(returns: ast.expr | None) -> str:
    """Short display label for ``Returns`` narrative (not necessarily one
    line).

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        returns: Primary returns used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if returns is None:
        return "None"
    if isinstance(returns, ast.Constant) and returns.value is None:
        return "None"
    label = (_unparse(returns) or "Any").replace("\n", " ").strip().strip("'\"")
    if len(label) > 64:
        label = label[:61] + "..."
    return label


def _return_type_line_for_google_block(returns: ast.expr | None, *, content_indent: str) -> str:
    """Single-line ``TypeName:`` tail for Google ``Returns:`` (audit regex
    + max 72 chars).

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        returns: Primary returns used by this step.
        content_indent: Primary content indent used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    leader = f"{content_indent}    "
    raw = (_unparse(returns) or "Any").replace("\n", " ").strip().strip("'\"")
    # ``leader + type + ':'`` must stay within the audit width (small margin).
    max_t = max(8, _GOOGLE_DOCSTRING_MAX_LINE - len(leader) - 2)
    if len(raw) > max_t:
        raw = raw[: max_t - 3] + "..."
    return raw


def _needs_returns_section(returns: ast.expr | None) -> bool:
    """Needs returns section.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        returns: Primary returns used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if returns is None:
        return False
    if isinstance(returns, ast.Constant) and returns.value is None:
        return False
    return True


def _iter_params_for_doc(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, ast.expr | None]]:
    """Yield params for doc.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        list[tuple[str, ast.expr | None]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[tuple[str, ast.expr | None]] = []
    for a in (*node.args.posonlyargs, *node.args.args):
        out.append((a.arg, a.annotation))
    if node.args.vararg:
        va = node.args.vararg
        out.append((f"*{va.arg}", va.annotation))
    for a in node.args.kwonlyargs:
        out.append((a.arg, a.annotation))
    if node.args.kwarg:
        ka = node.args.kwarg
        out.append((f"**{ka.arg}", ka.annotation))
    return out


def _params_for_google_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[str, ast.expr | None]]:
    """Params for google args.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        list[tuple[str, ast.expr | None]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    params = _iter_params_for_doc(node)
    if _callable_kind(node) == "method" and params and params[0][0] in ("self", "cls"):
        return params[1:]
    return params


def _wrap_to_width(text: str, *, width: int, initial: str, subsequent: str) -> list[str]:
    """Wrap to width.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        text: Text content to inspect or rewrite.
        width: Primary width used by this step.
        initial: Primary initial used by this step.
        subsequent: Primary subsequent used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if width < 12:
        width = 12
    wrapped = textwrap.wrap(
        text.strip(),
        width=width,
        initial_indent=initial,
        subsequent_indent=subsequent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapped or [initial.rstrip()]


def _split_identifier(name: str) -> list[str]:
    """Split snake_case or CamelCase identifiers into lowercase words.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        name: Primary name used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    cleaned = name.strip("_")
    if not cleaned:
        return []
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    return [part.lower() for part in snake.split("_") if part]


def _humanize_identifier(name: str, *, default: str = "value") -> str:
    """Return a readable phrase for an identifier.

    Args:
        name: Primary name used by this step.
        default: Primary default used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    parts = _split_identifier(name)
    return " ".join(parts) if parts else default


def _truncate_phrase(text: str, *, limit: int = 48) -> str:
    """Collapse whitespace and trim long snippets for compact prose.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        text: Text content to inspect or rewrite.
        limit: Primary limit used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _call_names_in_node(node: ast.AST) -> set[str]:
    """Collect direct call names used anywhere below *node*.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        set[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _function_summary(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a concise summary line for a function or method.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    parent = getattr(node, "parent", None)
    class_name = parent.name if isinstance(parent, ast.ClassDef) else None
    name = node.name

    if name == "__init__":
        return f"Initialize {class_name or 'the instance'}."
    if name == "__enter__":
        return "Enter the context manager and return the active resource."
    if name == "__exit__":
        return "Leave the context manager and release managed resources."
    if name.startswith("test_"):
        rest = _humanize_identifier(name[5:], default="the behavior")
        return f"Verify that {rest} works as expected."
    if name == "main":
        return "Run the command-line entry point."
    if name.startswith("visit_"):
        target = _humanize_identifier(name[6:], default="the target node")
        return f"Visit {target} nodes during AST traversal."

    parts = _split_identifier(name)
    if not parts:
        return f"Run ``{name}``."

    verb = parts[0]
    rest = " ".join(parts[1:])
    verb_map = {
        "build": "Build",
        "write": "Write",
        "read": "Read",
        "load": "Load",
        "save": "Save",
        "resolve": "Resolve",
        "parse": "Parse",
        "collect": "Collect",
        "find": "Find",
        "prepare": "Prepare",
        "create": "Create",
        "update": "Update",
        "remove": "Remove",
        "record": "Record",
        "register": "Register",
        "start": "Start",
        "finish": "Finish",
        "run": "Run",
        "check": "Check",
        "validate": "Validate",
        "audit": "Audit",
        "render": "Render",
        "format": "Format",
        "apply": "Apply",
        "repair": "Repair",
        "sync": "Synchronize",
        "ensure": "Ensure",
        "list": "List",
        "attach": "Attach",
        "compare": "Compare",
        "clean": "Clean",
        "reset": "Reset",
        "triage": "Triage",
        "inspect": "Inspect",
        "explain": "Explain",
        "import": "Import",
        "consolidate": "Consolidate",
    }
    if verb in {"is", "has", "can", "should"}:
        subject = rest or "the requested condition"
        return f"Return whether {subject}."
    if verb == "iter":
        subject = rest or "the requested items"
        return f"Yield {subject}."
    subject = rest or "the requested operation"
    return f"{verb_map.get(verb, verb.capitalize())} {subject}."


def _function_detail(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Return an optional detail paragraph when the body has notable
    behavior.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    calls = _call_names_in_node(node)
    details: list[str] = []
    if {"write_text", "write_json", "mkdir", "record_artifact", "write_payload_bundle"} & calls:
        details.append(
            "This callable writes or records artifacts as part of its workflow."
        )
    if any(isinstance(child, (ast.For, ast.AsyncFor, ast.While)) for child in ast.walk(node)):
        details.append(
            "The implementation iterates over intermediate items before it returns."
        )
    if any(isinstance(child, ast.Try) for child in ast.walk(node)):
        details.append(
            "Exceptions are normalized inside the implementation before control returns to callers."
        )
    if any(isinstance(child, ast.If) for child in ast.walk(node)):
        details.append(
            "Control flow branches on the parsed state rather than relying on one linear path."
        )
    if not details:
        return None
    return " ".join(details[:2])


def _parameter_description(
    name: str,
    annotation: ast.expr | None,
) -> str:
    """Return a concise parameter description based on the parameter name.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        name: Primary name used by this step.
        annotation: Primary annotation used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    raw = name.lstrip("*")
    lowered = raw.lower()
    ann = (_unparse(annotation) or "").lower()

    if lowered in {"self", "cls"}:
        return "The bound instance or class for this method call."
    if lowered.endswith(("_path", "_file")) or lowered in {"path", "file", "filepath", "filename"}:
        return "Filesystem path to the file or directory being processed."
    if lowered.endswith(("_dir", "_root")) or lowered in {"root", "repo_root", "target_repo_root"}:
        return "Root directory used to resolve repository-local paths."
    if lowered in {"query", "instruction", "prompt", "audience"}:
        return "Free-text input that shapes this operation."
    if lowered in {"mode", "status", "command"}:
        return f"Named {lowered.replace('_', ' ')} for this operation."
    if lowered in {"payload", "summary", "result", "record", "finding", "item"}:
        return "Structured data carried through this workflow."
    if lowered.endswith("_id") or lowered in {"run_id", "target_repo_id", "finding_id"}:
        return "Identifier used to select an existing run or record."
    if lowered in {"source", "text", "markdown", "doc", "inner"}:
        return "Text content to inspect or rewrite."
    if lowered in {"tree", "node", "func", "stmt"}:
        return "Parsed AST object being inspected or transformed."
    if lowered in {"args", "argv"}:
        return "Command-line arguments to parse for this invocation."
    if lowered.endswith("line") or lowered.endswith("_line") or lowered == "lineno":
        return "1-based source line number used by the audit or edit step."
    if lowered in {"include_tests", "include_private", "apply", "json", "exit_zero"} or ann == "bool":
        return "Whether to enable this optional behavior."
    label = _humanize_identifier(raw, default="this value")
    return f"Primary {label} used by this step."


def _returns_narrative(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a concise narrative for the ``Returns`` section.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    label = _return_type_label(node.returns)
    lowered = label.lower()
    if node.name == "main" and lowered == "int":
        return "Process exit status code for the invoked command."
    if "dict" in lowered or "mapping" in lowered:
        return "Structured payload describing the outcome of the operation."
    if lowered in {"path", "path | none"} or "path" in lowered:
        return "Filesystem path produced or resolved by this callable."
    if lowered == "bool":
        return "Boolean outcome for the requested condition check."
    if any(token in lowered for token in {"list", "tuple", "set", "sequence", "iterable", "iterator"}):
        return "Collection produced from the parsed or accumulated input data."
    if lowered == "str":
        return "Rendered text produced for downstream callers or writers."
    return f"Value produced by this callable as ``{label}``."


def _class_summary(node: ast.ClassDef) -> str:
    """Return a concise class summary derived from naming and base classes.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    base_names = [_unparse(base) or "" for base in node.bases]
    phrase = _humanize_identifier(node.name, default="this class")
    is_dataclass = any(
        isinstance(deco, ast.Name) and deco.id == "dataclass"
        or isinstance(deco, ast.Call)
        and isinstance(deco.func, ast.Name)
        and deco.func.id == "dataclass"
        for deco in node.decorator_list
    )

    if any("Exception" in base or base.endswith("Error") for base in base_names) or node.name.endswith("Error"):
        return f"Exception raised for {phrase}."
    if node.name.endswith("Adapter") and any(base.endswith("ABC") or base == "ABC" for base in base_names):
        target = _humanize_identifier(node.name.removesuffix("Adapter"), default="suite")
        return f"Abstract base class for {target} adapter workflows."
    if any(base.endswith("ABC") or base == "ABC" for base in base_names):
        return f"Abstract base class for {phrase}."
    if node.name.endswith("Adapter") or any(base.endswith("Adapter") for base in base_names):
        target = _humanize_identifier(node.name.removesuffix("Adapter"), default="suite")
        return f"Adapter implementation for {target} workflows."
    if node.name.endswith("Registry"):
        target = _humanize_identifier(node.name.removesuffix("Registry"), default="registry")
        return f"Registry for {target} records."
    if node.name.endswith("Service"):
        target = _humanize_identifier(node.name.removesuffix("Service"), default="service")
        return f"Service object for {target} operations."
    if node.name.endswith("Manager"):
        target = _humanize_identifier(node.name.removesuffix("Manager"), default="manager")
        return f"Manager for {target} operations."
    if node.name.endswith("Ref"):
        target = _humanize_identifier(node.name.removesuffix("Ref"), default="the target object")
        return f"Reference to {target}."
    if node.name.endswith("Result"):
        target = _humanize_identifier(node.name.removesuffix("Result"), default="the operation")
        return f"Structured result returned by {target} workflows."
    if node.name.endswith(("Record", "Entry", "Config")) or is_dataclass:
        return f"Structured data container for {phrase}."
    return f"Coordinate {phrase} behavior."


def _module_summary(rel_posix: str) -> str:
    """Return a concise module summary for the given repository-relative
    path.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        rel_posix: Primary rel posix used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    path = Path(rel_posix)
    stem = path.stem
    package_parts = [part for part in path.parts[:-1] if part != "'fy'-suites"]
    package = ".".join(package_parts)

    if path.name == "__init__.py":
        target = package or path.parent.as_posix()
        return f"Package exports for {target}."
    if path.name == "__main__.py":
        target = package or path.parent.as_posix()
        return f"Module entry point for {target}."
    if "tests" in path.parts or stem.startswith("test_"):
        target = _humanize_identifier(stem.removeprefix("test_"), default="the covered behavior")
        return f"Tests for {target}."
    if stem == "cli":
        target = package or path.parent.as_posix()
        return f"Command-line interface for {target}."
    if stem == "service":
        target = package or path.parent.as_posix()
        return f"Service helpers for {target}."
    phrase = _humanize_identifier(stem, default="module utilities")
    if package:
        return f"{phrase.capitalize()} for {package}."
    return f"{phrase.capitalize()}."


def build_google_docstring_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    content_indent: str,
    summary_override: str | None = None,
) -> list[str]:
    """Build docstring inner lines for a function or method.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.
        content_indent: Primary content indent used by this step.
        summary_override: Primary summary override used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    ci = content_indent
    lines_out: list[str] = []

    summary = " ".join((summary_override or _function_summary(node)).split())
    lines_out.extend(
        _wrap_to_width(
            summary,
            width=_DOCSTRING_FLOW_WIDTH,
            initial=ci,
            subsequent=ci,
        )
    )

    detail = _function_detail(node)
    if detail:
        lines_out.append("")
        lines_out.extend(
            _wrap_to_width(
                detail,
                width=_DOCSTRING_FLOW_WIDTH,
                initial=ci,
                subsequent=ci,
            )
        )

    params = _params_for_google_args(node)
    if params:
        lines_out.append("")
        lines_out.append(f"{ci}Args:")
        arg_prefix = f"{ci}    "
        for pname, ann in params:
            desc = _parameter_description(pname, ann)
            leader = f"{arg_prefix}{pname}: "
            cont = f"{arg_prefix}    "
            wrapped = textwrap.wrap(
                desc.strip(),
                width=_DOCSTRING_FLOW_WIDTH,
                initial_indent=leader,
                subsequent_indent=cont,
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines_out.extend(wrapped if wrapped else [leader.rstrip()])

    if _needs_returns_section(node.returns):
        lines_out.append("")
        lines_out.append(f"{ci}Returns:")
        type_line = _return_type_line_for_google_block(
            node.returns,
            content_indent=ci,
        )
        lines_out.append(f"{ci}    {type_line}:")
        body = _returns_narrative(node)
        narr_prefix = f"{ci}        "
        fill_w = _DOCSTRING_FLOW_WIDTH - len(narr_prefix)
        lines_out.extend(
            _wrap_to_width(
                body,
                width=max(16, fill_w),
                initial=narr_prefix,
                subsequent=narr_prefix,
            )
        )

    while lines_out and lines_out[-1].strip() == "":
        lines_out.pop()
    return lines_out


def _apply_google_docstring_same_line_function_body(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    stmt0: ast.stmt,
    raw_lines: list[str],
    plain: list[str],
) -> tuple[str | None, str | None]:
    """Handle ``def foo(...): <suite>`` when *suite* starts on the same
    line as ``def``.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        func: Parsed AST object being inspected or transformed.
        stmt0: Primary stmt0 used by this step.
        raw_lines: Primary raw lines used by this step.
        plain: Primary plain used by this step.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if stmt0.col_offset is None:
        return None, "single-line function body missing col_offset (cannot splice docstring)"
    idx = (func.lineno or 1) - 1
    if not (0 <= idx < len(raw_lines)):
        return None, "function lineno out of range"
    line = raw_lines[idx]
    cut = stmt0.col_offset
    if cut > len(line):
        return None, "col_offset past line end"
    head = line[:cut]
    tail = line[cut:].lstrip()
    def_indent = _indent_for_line(plain, func.lineno or 1)
    content_indent = f"{def_indent}    "
    new_stmt = format_function_docstring_block(func, content_indent=content_indent)
    merged = f"{head.rstrip()}\n{new_stmt}{content_indent}{tail}"
    out_lines = raw_lines[:idx] + [merged] + raw_lines[idx + 1 :]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def format_function_docstring_block(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    content_indent: str,
    summary_override: str | None = None,
) -> str:
    """Return a full triple-quoted docstring assignment (first body
    statement).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.
        content_indent: Primary content indent used by this step.
        summary_override: Primary summary override used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    inner_lines = build_google_docstring_lines(
        node,
        content_indent=content_indent,
        summary_override=summary_override,
    )
    if not inner_lines:
        inner_lines = [f"{content_indent}Empty docstring."]
    first_line = inner_lines[0]
    if not first_line.startswith(content_indent):
        first_line = f"{content_indent}{first_line.lstrip()}"
    first_text = first_line[len(content_indent) :]
    parts: list[str] = [f'{content_indent}"""{first_text}']
    for ln in inner_lines[1:]:
        parts.append("\n" + ln)
    parts.append(f'\n{content_indent}"""\n')
    return "".join(parts)


def apply_google_docstring_to_function_node(
    source: str,
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str | None, str | None]:
    """Insert or replace the docstring on a concrete function or method
    *func*.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        func: Parsed AST object being inspected or transformed.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not func.body:
        return None, f"function {func.name!r} has no body"

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    stmt0 = func.body[0]
    end_ln = getattr(stmt0, "end_lineno", None) or stmt0.lineno or 1
    if (
        func.lineno == stmt0.lineno == end_ln
        and getattr(stmt0, "col_offset", None) is not None
        and not (
            isinstance(stmt0, ast.Expr)
            and isinstance(stmt0.value, ast.Constant)
            and isinstance(stmt0.value.value, str)
        )
    ):
        return _apply_google_docstring_same_line_function_body(func, stmt0, raw_lines, plain)

    content_indent = _indent_for_line(plain, stmt0.lineno)
    new_stmt = format_function_docstring_block(func, content_indent=content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)

    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def format_class_docstring_block(node: ast.ClassDef, *, content_indent: str) -> str:
    """Return a class docstring block derived from the class shape.

    Args:
        node: Parsed AST object being inspected or transformed.
        content_indent: Leading whitespace used for continued docstring
            lines in the source file.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    width = _docstring_reflow_width(content_indent)
    inner = reflow_plain_docstring_paragraphs(_class_summary(node), width=width)
    return format_function_docstring_from_dedented_body(inner, content_indent)


def apply_google_docstring_to_class_node(source: str, node: ast.ClassDef) -> tuple[str | None, str | None]:
    """Insert or replace the docstring on a concrete *ClassDef*.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        node: Parsed AST object being inspected or transformed.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not node.body:
        return None, f"class {node.name!r} has no body"

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, node.body[0].lineno)
    new_stmt = format_class_docstring_block(node, content_indent=content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)

    stmt0 = node.body[0]
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def _header_insert_line_index(lines: list[str]) -> int:
    """Return 0-based index where a new module docstring line block should
    be inserted.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        lines: Primary lines used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "":
            i += 1
            continue
        if stripped.startswith("#") and ("coding:" in stripped or "coding=" in stripped):
            i += 1
            continue
        break
    return i


def apply_module_google_docstring(source: str, *, rel_posix: str) -> tuple[str | None, str | None]:
    """Insert or replace a file-level module docstring (PEP 257, before
    ``from __future__``).

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        rel_posix: Primary rel posix used by this step.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return None, f"parse error: {exc}"

    doc = ast.get_docstring(tree, clean=False)
    if doc is not None and doc.strip():
        return source, None

    summary_inner = reflow_plain_docstring_paragraphs(_module_summary(rel_posix))
    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]

    if tree.body:
        first = tree.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(
            first.value.value, str
        ):
            if not first.value.value.strip():
                content_indent = _indent_for_line(plain, first.lineno)
                if content_indent.strip():
                    new_stmt = format_function_docstring_from_dedented_body(summary_inner, content_indent)
                else:
                    new_stmt = format_top_module_docstring_block(summary_inner)
                new_stmt_lines = new_stmt.splitlines(keepends=True)
                start_idx = first.lineno - 1
                end_idx = (first.end_lineno or first.lineno) - 1
                out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
                new_source = "".join(out_lines)
                try:
                    ast.parse(new_source)
                except SyntaxError as exc:
                    return None, f"post-edit parse error: {exc}"
                return new_source, None

    insert_at = _header_insert_line_index(raw_lines)
    block = format_top_module_docstring_block(summary_inner)
    out_lines = raw_lines[:insert_at] + [block] + raw_lines[insert_at:]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_module_docstring_in_source(
    source: str,
    tree: ast.Module,
    *,
    rel_posix: str | None = None,
) -> tuple[str | None, str | None]:
    """Repair an existing module docstring when layout or quality drifts.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        tree: Parsed AST object being inspected or transformed.
        rel_posix: Primary rel posix used by this step.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    doc = ast.get_docstring(tree, clean=False) or ""
    if not doc.strip():
        return source, None
    if not (_google_audit_doc_has_long_line(doc) or _docstring_looks_generated_or_noisy(doc)):
        return source, None

    new_inner = reflow_plain_docstring_paragraphs(doc)
    if (new_inner.strip() == doc.strip() or _docstring_looks_generated_or_noisy(doc)) and rel_posix:
        new_inner = reflow_plain_docstring_paragraphs(_module_summary(rel_posix))
    if new_inner.strip() == doc.strip():
        return source, None
    if not tree.body:
        return None, "empty module"

    first = tree.body[0]
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return None, "module docstring is not a leading string literal"

    new_block = format_top_module_docstring_block(new_inner)
    new_stmt_lines = new_block.splitlines(keepends=True)
    raw_lines = source.splitlines(keepends=True)
    start_idx = first.lineno - 1
    end_idx = (first.end_lineno or first.lineno) - 1
    new_source = "".join(raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :])
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_class_docstring_in_source(source: str, node: ast.ClassDef) -> tuple[str | None, str | None]:
    """Repair an existing class docstring when layout or quality drifts.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        node: Parsed AST object being inspected or transformed.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    doc = ast.get_docstring(node, clean=False) or ""
    if not doc.strip():
        return source, None
    if not (_google_audit_doc_has_long_line(doc) or _docstring_looks_generated_or_noisy(doc)):
        return source, None
    if not node.body:
        return None, f"class {node.name!r} has no body"

    stmt0 = node.body[0]
    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, stmt0.lineno)
    width = _docstring_reflow_width(content_indent)
    new_inner = reflow_plain_docstring_paragraphs(doc, width=width)
    if _docstring_looks_generated_or_noisy(doc):
        new_inner = reflow_plain_docstring_paragraphs(_class_summary(node), width=width)
    if new_inner.strip() == doc.strip():
        return source, None

    new_stmt = format_function_docstring_from_dedented_body(new_inner, content_indent)
    new_stmt_lines = new_stmt.splitlines(keepends=True)
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]
    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def repair_function_google_docstring_in_source(
    source: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str | None, str | None]:
    """Align function/method docstrings with Google audit (width,
    ``Args:``, ``Returns:``).

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        node: Parsed AST object being inspected or transformed.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if not node.body:
        return source, None

    doc = ast.get_docstring(node, clean=False) or ""
    doc_clean = ast.get_docstring(node, clean=True) or ""
    if not doc.strip():
        return source, None

    stmt0 = node.body[0]
    end_ln = getattr(stmt0, "end_lineno", None) or stmt0.lineno or 1
    if (
        node.lineno == stmt0.lineno == end_ln
        and getattr(stmt0, "col_offset", None) is not None
        and isinstance(stmt0, ast.Expr)
        and isinstance(stmt0.value, ast.Constant)
        and isinstance(stmt0.value.value, str)
    ):
        return apply_google_docstring_to_function_node(source, node)

    missing_a = _google_audit_missing_args_section(node, doc)
    missing_r = _google_audit_missing_returns_section(node, doc)
    long_l = _google_audit_doc_has_long_line(doc)
    bad_ret = _google_returns_type_line_invalid(node, doc)
    noisy_doc = _docstring_looks_generated_or_noisy(doc)
    if not (missing_a or missing_r or long_l or bad_ret or noisy_doc):
        return source, None

    raw_lines = source.splitlines(keepends=True)
    plain = [ln.rstrip("\n") for ln in raw_lines]
    content_indent = _indent_for_line(plain, stmt0.lineno)

    summary = _first_summary_paragraph_for_reuse(doc_clean)
    new_stmt = format_function_docstring_block(
        node,
        content_indent=content_indent,
        summary_override=summary,
    )

    new_stmt_lines = new_stmt.splitlines(keepends=True)
    start_idx = stmt0.lineno - 1
    if isinstance(stmt0, ast.Expr) and isinstance(stmt0.value, ast.Constant) and isinstance(
        stmt0.value.value, str
    ):
        end_idx = (stmt0.end_lineno or stmt0.lineno) - 1
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[end_idx + 1 :]
    else:
        out_lines = raw_lines[:start_idx] + new_stmt_lines + raw_lines[start_idx:]

    new_source = "".join(out_lines)
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return None, f"post-edit parse error: {exc}"
    return new_source, None


def apply_function_google_docstring(source: str, func_name: str) -> tuple[str | None, str | None]:
    """Parse *source*, replace or insert a Google-style docstring for
    *func_name*.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        func_name: Primary func name used by this step.

    Returns:
        tuple[str | None, str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return None, f"parse error: {exc}"

    _attach_parents(tree)
    func = _find_function(tree, func_name)
    if func is None:
        return None, f"no function named {func_name!r}"
    return apply_google_docstring_to_function_node(source, func)


def _format_block_comment(indent: str, prose: str) -> list[str]:
    """Turn *prose* into PEP 8 style ``#`` lines at *indent*.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        indent: Primary indent used by this step.
        prose: Primary prose used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    available = max(20, _COMMENT_FLOW_WIDTH - len(indent) - 2)
    wrapped = textwrap.wrap(
        prose.strip(),
        width=available,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped:
        return [f"{indent}#"]
    out: list[str] = []
    for i, seg in enumerate(wrapped):
        out.append(f"{indent}# {seg}" if seg else f"{indent}#")
    return out


def _describe_statement(stmt: ast.stmt) -> str:
    """English explanation from AST shape; two short sentences where
    helpful.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        stmt: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if isinstance(stmt, ast.If):
        try:
            cond = ast.unparse(stmt.test)
        except AttributeError:
            cond = "the condition"
        if len(cond) > 65:
            cond = cond[:62] + "..."
        orelse = stmt.orelse
        extra = ""
        if orelse and not (len(orelse) == 1 and isinstance(orelse[0], ast.If)):
            extra = " The else branch covers the complementary case."
        elif orelse:
            extra = " elif/else ladders chain further decisions below."
        return (
            f"Branch when {cond}. Readers should compare both arms for data flow and invariants."
            + extra
        )
    if isinstance(stmt, ast.Assign):
        if (
            len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Constant)
            and stmt.value.value is None
        ):
            return (
                f"Reset ``{stmt.targets[0].id}`` to a known baseline before conditional updates. "
                f"That keeps later branches from reusing stale values when the guard skips them."
            )
        targets = [ast.unparse(t) for t in stmt.targets]
        try:
            rhs = ast.unparse(stmt.value)
        except AttributeError:
            rhs = "the right-hand expression"
        if len(rhs) > 45:
            rhs = rhs[:42] + "..."
        return (
            f"Bind {' , '.join(targets)} to {rhs}. "
            f"Names introduced here should stay consistent for the rest of the block."
        )
    if isinstance(stmt, ast.AnnAssign):
        try:
            ann = ast.unparse(stmt.annotation)
        except AttributeError:
            ann = "annotation"
        return (
            f"Declare or narrow a typed slot using {ann}. "
            f"Callers and type checkers both rely on this shape staying truthful."
        )
    if isinstance(stmt, ast.Return):
        if isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name:
                return (
                    f"Produce the final ``{name}(...)`` value for this path. "
                    f"Keyword arguments encode the payload; adjust them when the dataclass or API evolves."
                )
        try:
            val = ast.unparse(stmt.value) if stmt.value else "nothing"
        except AttributeError:
            val = "a value"
        if len(val) > 55:
            val = "a structured value"
        return f"Exit with {val}. Ensure this matches the function's advertised contract to callers."
    if isinstance(stmt, ast.For):
        return (
            "Iterate with a clear loop variable and predictable side effects. "
            "Prefer extracting non-trivial body logic so reviewers can follow each pass."
        )
    if isinstance(stmt, ast.While):
        return (
            "Repeat until the guard becomes false; watch for infinite loops when external state stalls. "
            "Document any intentional busy-wait or polling behaviour in adjacent comments."
        )
    if isinstance(stmt, ast.With):
        return (
            "Acquire managed resources for the nested suite and release them on exit. "
            "Exceptions should still leave the context protocol in a valid teardown path."
        )
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        try:
            call = ast.unparse(stmt.value)
        except AttributeError:
            call = "a call"
        if len(call) > 50:
            call = call[:47] + "..."
        return (
            f"Evaluate ``{call}`` for its side effect (return value discarded). "
            f"State touched here should be obvious from the callee name or nearby assignments."
        )
    return (
        "Logical step in the surrounding control flow. "
        "Tie it back to the function docstring or module overview when behaviour is non-obvious."
    )


def plan_block_comments(
    source: str,
    *,
    start_line: int,
    end_line: int,
    function_name: str | None,
) -> tuple[list[tuple[int, list[str]]], str | None]:
    """Return (insertions, error) where each insertion is (1-based line
    before which to insert, list of new comment lines).

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        source: Text content to inspect or rewrite.
        start_line: 1-based source line number used by the audit or edit
            step.
        end_line: 1-based source line number used by the audit or edit
            step.
        function_name: Primary function name used by this step.

    Returns:
        tuple[list[tuple[int, list[str]]], str | None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], f"parse error: {exc}"

    if function_name:
        fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                fn = node
                break
        if fn is None:
            return [], f"no function named {function_name!r}"
        if not fn.body:
            return [], f"function {function_name!r} has no body"
        first = _stmt_span(fn.body[0])[0]
        last = max(_stmt_span(st)[1] for st in fn.body)
        start_line, end_line = first, last

    target_fn = _function_spanning_range(tree, start_line, end_line)
    body: Sequence[ast.stmt]
    if target_fn is not None:
        body = target_fn.body
    else:
        body = tree.body

    inserts: list[tuple[int, list[str]]] = []
    for stmt in body:
        sl, el = _stmt_span(stmt)
        if not _intersects(sl, el, start_line, end_line):
            continue
        indent = _indent_for_line(lines, sl)
        prose = _describe_statement(stmt)
        block = _format_block_comment(indent, prose)
        if not block:
            continue
        inserts.append((sl, block))

    inserts.sort(key=lambda x: x[0], reverse=True)
    return inserts, None


def apply_planned_comments(path: Path, inserts: list[tuple[int, list[str]]]) -> None:
    """Apply planned comments.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        path: Filesystem path to the file or directory being processed.
        inserts: Primary inserts used by this step.
    """
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    for lineno, block in inserts:
        idx = lineno - 1
        for i, comment_line in enumerate(block):
            lines.insert(idx + i, comment_line)
    out = "\n".join(lines) + ("\n" if raw.endswith("\n") else "")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(out, encoding="utf-8", newline="\n")


@dataclass
class BlockInsert:
    """One planned comment insertion."""

    before_line: int
    lines: list[str]


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point.

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
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--file", type=Path, required=True, help="Python file to edit (repo-relative or absolute).")
    parser.add_argument("--start-line", type=int, default=None)
    parser.add_argument("--end-line", type=int, default=None)
    parser.add_argument(
        "--function",
        type=str,
        default=None,
        help="Use this function's full body span (comments) or target name (Google docstring mode).",
    )
    parser.add_argument("--apply", action="store_true", help="Write comment insertions to the file (comments mode).")
    parser.add_argument(
        "--emit-google-docstring",
        action="store_true",
        help="Emit a Google-style docstring draft for ``--function`` instead of ``#`` comments.",
    )
    parser.add_argument(
        "--apply-docstring",
        action="store_true",
        help="Write ``--emit-google-docstring`` output to the file (implies review in git diff).",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.emit_google_docstring:
        if not args.function:
            parser.error("--emit-google-docstring requires --function NAME")
        if args.start_line is not None or args.end_line is not None:
            parser.error("--emit-google-docstring does not use --start-line / --end-line")
        if args.apply and args.apply_docstring:
            parser.error("use either --apply (comments) or --apply-docstring (docstring), not both")
        if args.apply:
            parser.error("with --emit-google-docstring use --apply-docstring to write the file, not --apply")
    elif args.apply_docstring:
        parser.error("--apply-docstring requires --emit-google-docstring")
    elif args.function:
        if args.start_line is not None or args.end_line is not None:
            parser.error("with --function, omit --start-line and --end-line (body span is derived from AST).")
    elif args.start_line is None or args.end_line is None:
        parser.error("pass --start-line and --end-line, or pass --function alone, or use --emit-google-docstring.")

    repo_root = (args.repo_root or Path(__file__).resolve().parents[3]).resolve()
    target = args.file
    path = target.resolve() if target.is_absolute() else (repo_root / target).resolve()
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2

    source = path.read_text(encoding="utf-8-sig")
    rel = path.relative_to(repo_root).as_posix()

    if args.emit_google_docstring:
        new_src, err = apply_function_google_docstring(source, args.function)
        if err or new_src is None:
            print(err or "unknown error", file=sys.stderr)
            return 2
        tree2 = ast.parse(source)
        _attach_parents(tree2)
        fn2 = _find_function(tree2, args.function)
        if fn2 is None or not fn2.body:
            print("internal error: function missing after successful transform preview", file=sys.stderr)
            return 2
        ci = _indent_for_line(source.splitlines(), fn2.body[0].lineno)
        preview = format_function_docstring_block(fn2, content_indent=ci)
        payload: dict[str, object] = {
            "repo_root": str(repo_root),
            "file": rel,
            "mode": "google_docstring",
            "function": args.function,
            "dry_run": not args.apply_docstring,
            "docstring_block": preview,
        }
        if args.json or args.out:
            text = json.dumps(payload, indent=2) + "\n"
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                # Write the human-readable companion text so reviewers can inspect the
                # result without opening raw structured data.
                args.out.write_text(text, encoding="utf-8")
            else:
                sys.stdout.write(text)
        else:
            print(payload["docstring_block"], end="")

        if args.apply_docstring:
            path.write_text(new_src, encoding="utf-8", newline="\n")
        return 0

    start_line = args.start_line if args.start_line is not None else 1
    end_line = args.end_line if args.end_line is not None else 10**9
    inserts, err = plan_block_comments(
        source,
        start_line=int(start_line),
        end_line=int(end_line),
        function_name=args.function,
    )
    if err:
        print(err, file=sys.stderr)
        return 2

    payload = {
        "repo_root": str(repo_root),
        "file": rel,
        "mode": "block_comments",
        "dry_run": not args.apply,
        "insertions": [asdict(BlockInsert(before_line=a, lines=b)) for a, b in inserts],
    }

    if args.json or args.out:
        text = json.dumps(payload, indent=2) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    else:
        print(f"Planned insertions before lines: {[i for i, _ in inserts]}")
        for before, block in inserts:
            print(f"\n--- before line {before} ---")
            print("\n".join(block))

    if args.apply and inserts:
        apply_planned_comments(path, inserts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
