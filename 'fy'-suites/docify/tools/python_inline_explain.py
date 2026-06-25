"""Python inline explain for docify.tools.

"""
from __future__ import annotations

import argparse
import ast
import re
import textwrap
from pathlib import Path
from typing import Iterable, Sequence

FLOW_WIDTH = 88


CONTROL_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)

GENERATED_COMMENT_MARKERS = (
    "prepare the local state",
    "branch on ",
    "return the final outward-facing result",
    "append a journal-style event",
    "run the side-effecting helper",
    "process ",
    "stay in this loop",
    "read and normalize the input data",
    "assemble the structured result data",
    "build filesystem locations and shared state",
    "persist the current phase output",
    "wire together the shared services",
    "protect the critical",
    "enter a managed resource scope",
    "continue the internal",
)


def _attach_parents(node: ast.AST) -> None:
    """Populate ``parent`` links so qualified names can be derived.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        node: Parsed AST object being inspected or transformed.
    """
    # Process child one item at a time so _attach_parents applies the same rule across
    # the full collection.
    for child in ast.iter_child_nodes(node):
        setattr(child, "parent", node)  # noqa: B010
        _attach_parents(child)


def _qualified_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
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


def _find_function(
    tree: ast.Module,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the callable matching *name* or ``Class.method``.

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
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == name or _qualified_name(node) == name:
            return node
    return None


def _line_indent(lines: list[str], lineno: int) -> str:
    """Return the leading whitespace for the given 1-based source line.

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
    idx = max(lineno - 1, 0)
    if idx >= len(lines):
        return ""
    raw = lines[idx]
    return raw[: len(raw) - len(raw.lstrip())]


def _comment_lines(indent: str, text: str) -> list[str]:
    """Wrap *text* into comment lines that fit inside the configured width.

    Args:
        indent: Primary indent used by this step.
        text: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    wrapped = textwrap.wrap(
        text,
        width=max(40, FLOW_WIDTH - len(indent) - 2),
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [f"{indent}# {line}" for line in wrapped] if wrapped else [f"{indent}#"]


def _call_name(node: ast.AST) -> str:
    """Return a short callee label for direct call expressions.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    return ""


def _truncate(text: str, *, limit: int = 48) -> str:
    """Return a compact single-line preview string.

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


def _humanize_identifier(name: str, *, default: str) -> str:
    """Turn snake_case or CamelCase identifiers into a human phrase.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        name: Primary name used by this step.
        default: Primary default used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    cleaned = name.strip("_")
    if not cleaned:
        return default
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    words = [part.lower() for part in snake.split("_") if part]
    return " ".join(words) if words else default


def _existing_comment_block(lines: list[str], lineno: int, indent: str) -> list[str]:
    """Return the contiguous comment block directly above *lineno*.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        lines: Primary lines used by this step.
        lineno: 1-based source line number used by the audit or edit
            step.
        indent: Primary indent used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    idx = lineno - 2
    block: list[str] = []
    while idx >= 0:
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith("#") and line.startswith(indent):
            block.append(line)
            idx -= 1
            continue
        break
    block.reverse()
    return block


def _looks_tool_generated_comment_block(block: list[str]) -> bool:
    """Return whether *block* matches Docify-owned inline comments.

    Args:
        block: Primary block used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition check.
    """
    joined = " ".join(line.strip().lstrip("#").strip() for line in block).lower()
    return any(marker in joined for marker in GENERATED_COMMENT_MARKERS)


def scrub_generated_inline_comments(source: str) -> str:
    """Remove previously generated Docify inline comment blocks.

    Args:
        source: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = source.splitlines()
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("#"):
            indent = line[: len(line) - len(line.lstrip())]
            block: list[str] = []
            end = index
            while end < len(lines):
                candidate = lines[end]
                candidate_stripped = candidate.strip()
                if candidate_stripped.startswith("#") and candidate.startswith(indent):
                    block.append(candidate)
                    end += 1
                    continue
                break
            if block and _looks_tool_generated_comment_block(block):
                index = end
                continue
        cleaned.append(line)
        index += 1
    return "\n".join(cleaned) + ("\n" if source.endswith("\n") else "")


def _body_without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """Drop the leading docstring expression when present.

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


def _body_has_control_flow(body: Iterable[ast.stmt]) -> bool:
    """Return whether *body* contains non-trivial branching or looping.

    Args:
        body: Primary body used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return any(isinstance(stmt, CONTROL_NODES) for stmt in body)


def _should_annotate_group(group: list[ast.stmt], *, lines: list[str]) -> bool:
    """Return whether a grouped phase deserves an inline explanation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        group: Primary group used by this step.
        lines: Primary lines used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if not group:
        return False
    if len(group) > 1:
        return True
    stmt = group[0]
    if isinstance(stmt, CONTROL_NODES + (ast.Return,)):
        return True
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr)):
        return True
    return False


def _group_statements(body: list[ast.stmt]) -> list[list[ast.stmt]]:
    """Group consecutive setup statements into larger workflow phases.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        body: Primary body used by this step.

    Returns:
        list[list[ast.stmt]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    groups: list[list[ast.stmt]] = []
    current: list[ast.stmt] = []

    def flush() -> None:
        """Flush the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.
        """
        nonlocal current
        if current:
            groups.append(current)
            current = []

    for stmt in body:
        simple_setup = isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        if simple_setup:
            current.append(stmt)
            continue
        flush()
        groups.append([stmt])
    flush()
    return groups


def _describe_assignment_group(group: list[ast.stmt], function_name: str) -> str:
    """Summarize a cluster of assignments or helper calls.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        group: Primary group used by this step.
        function_name: Primary function name used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    targets: list[str] = []
    calls: list[str] = []
    for stmt in group:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)
            if isinstance(stmt.value, ast.Call):
                call = _call_name(stmt.value)
                if call:
                    calls.append(call)
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                targets.append(stmt.target.id)
            if isinstance(stmt.value, ast.Call):
                call = _call_name(stmt.value)
                if call:
                    calls.append(call)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = _call_name(stmt.value)
            if call:
                calls.append(call)

    joined_targets = " ".join(targets).lower()
    joined_calls = " ".join(calls).lower()
    if any(token.endswith(("_path", "_dir", "_root")) for token in targets):
        return (
            f"Build filesystem locations and shared state that the rest of "
            f"{function_name} reuses."
        )
    if any(key in joined_targets for key in {"payload", "summary", "finding"}):
        return (
            f"Assemble the structured result data before later steps enrich or "
            f"return it from {function_name}."
        )
    if any(key in joined_targets for key in {"registry", "journal", "index", "router", "context"}):
        return (
            f"Wire together the shared services that {function_name} depends on "
            f"for the rest of its workflow."
        )
    if any(call in joined_calls for call in {"read_text", "load", "parse", "loads"}):
        return (
            f"Read and normalize the input data before {function_name} branches on "
            f"or transforms it further."
        )
    if any(call in joined_calls for call in {"write_text", "write_json", "mkdir", "record_artifact"}):
        return (
            f"Persist the current phase output so the remaining {function_name} "
            f"steps can rely on a stable on-disk artifact."
        )
    return f"Prepare the local state that the next stage of {function_name} consumes."


def _describe_statement(stmt: ast.stmt, function_name: str) -> str:
    """Return a context-first explanation for a single statement.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        stmt: Parsed AST object being inspected or transformed.
        function_name: Primary function name used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if isinstance(stmt, ast.If):
        condition = _truncate(ast.unparse(stmt.test) if hasattr(ast, "unparse") else "the condition")
        return (
            f"Branch on {condition} so {function_name} only continues along the "
            f"matching state path."
        )
    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        target = _truncate(ast.unparse(stmt.target) if hasattr(ast, "unparse") else "each item")
        return (
            f"Process {target} one item at a time so {function_name} applies the "
            f"same rule across the full collection."
        )
    if isinstance(stmt, ast.While):
        condition = _truncate(ast.unparse(stmt.test) if hasattr(ast, "unparse") else "the guard")
        return (
            f"Stay in this loop only while {condition} remains true, so callers do "
            f"not observe a half-finished {function_name} state."
        )
    if isinstance(stmt, ast.Try):
        return (
            f"Protect the critical {function_name} work so failures can be turned "
            f"into a controlled result or cleanup path."
        )
    if isinstance(stmt, (ast.With, ast.AsyncWith)):
        return (
            f"Enter a managed resource scope for this phase and rely on the context "
            f"manager to clean up when {function_name} leaves it."
        )
    if isinstance(stmt, ast.Return):
        return (
            f"Return the final outward-facing result only after the earlier "
            f"{function_name} preparation is complete."
        )
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = _call_name(stmt.value)
        if call == "write_json":
            return (
                "Persist the structured JSON representation so automated tooling "
                "can consume the result without reparsing prose."
            )
        if call == "write_text":
            return (
                "Write the human-readable companion text so reviewers can inspect "
                "the result without opening raw structured data."
            )
        if call == "record_artifact":
            return (
                "Register the written artifact in the evidence registry so later "
                "status and compare flows can discover it."
            )
        if call == "append":
            return (
                f"Append a journal-style event so later {function_name} reads can "
                "reconstruct what happened during this run."
            )
        return f"Run the side-effecting helper that advances the {function_name} workflow."
    return f"Continue the internal {function_name} control flow with this step."


def _collect_plans_for_body(
    body: list[ast.stmt],
    *,
    function_name: str,
    lines: list[str],
) -> list[tuple[int, list[str]]]:
    """Return grouped comment blocks for one statement body.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        body: Primary body used by this step.
        function_name: Primary function name used by this step.
        lines: Primary lines used by this step.

    Returns:
        list[tuple[int, list[str]]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    plans: list[tuple[int, list[str]]] = []
    groups = _group_statements(_body_without_docstring(body))
    for group in groups:
        if not _should_annotate_group(group, lines=lines):
            continue
        first = group[0]
        lineno = int(getattr(first, "lineno", 1))
        indent = _line_indent(lines, lineno)
        block = _existing_comment_block(lines, lineno, indent)
        if block and not _looks_tool_generated_comment_block(block):
            continue
        if len(group) > 1 or isinstance(group[0], (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            prose = _describe_assignment_group(group, function_name)
        else:
            prose = _describe_statement(group[0], function_name)
        if prose.startswith((
            "Prepare the local state",
            "Return the final outward-facing result",
            "Run the side-effecting helper",
            "Append a journal-style event",
            "Continue the internal",
        )):
            continue
        plans.append((lineno, _comment_lines(indent, prose)))

        stmt = group[0]
        nested_bodies: list[list[ast.stmt]] = []
        if isinstance(stmt, ast.If):
            nested_bodies.extend([stmt.body, stmt.orelse])
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            nested_bodies.extend([stmt.body, stmt.orelse])
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            nested_bodies.append(stmt.body)
        elif isinstance(stmt, ast.Try):
            nested_bodies.extend([stmt.body, stmt.orelse, stmt.finalbody])
            nested_bodies.extend(handler.body for handler in stmt.handlers)
        for nested in nested_bodies:
            nested = _body_without_docstring(nested)
            if len(nested) < 2 and not _body_has_control_flow(nested):
                continue
            plans.extend(
                _collect_plans_for_body(
                    nested,
                    function_name=function_name,
                    lines=lines,
                )
            )
    return plans


def annotate_function_inline(source: str, function_name: str, mode: str = "dense") -> str:
    """Insert grouped inline comments for the named callable.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        source: Text content to inspect or rewrite.
        function_name: Primary function name used by this step.
        mode: Named mode for this operation.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    source = scrub_generated_inline_comments(source)
    tree = ast.parse(source)
    _attach_parents(tree)
    fn = _find_function(tree, function_name)
    if fn is None:
        raise ValueError(f"function_not_found:{function_name}")

    lines = source.splitlines()
    body = _body_without_docstring(list(fn.body))
    if not body:
        return source

    plans = _collect_plans_for_body(
        body,
        function_name=function_name.split(".")[-1],
        lines=lines,
    )
    if mode == "block":
        plans = [
            (lineno, _comment_lines(_line_indent(lines, lineno), "Block purpose: " + " ".join(line[2:].strip() for line in block)))
            for lineno, block in plans
        ]
    if not plans:
        return source

    new_lines = lines[:]
    for lineno, comment_lines in sorted(plans, key=lambda item: item[0], reverse=True):
        idx = max(lineno - 1, 0)
        new_lines[idx:idx] = comment_lines
    return "\n".join(new_lines) + ("\n" if source.endswith("\n") else "")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for grouped inline explanation generation.

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
        description="Generate grouped inline explanations for a Python function."
    )
    parser.add_argument("--file", required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--mode", choices=["dense", "block"], default="dense")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args(list(argv) if argv is not None else None)

    path = Path(args.file).expanduser().resolve()
    source = path.read_text(encoding="utf-8")
    rendered = annotate_function_inline(source, args.function, mode=args.mode)

    if args.apply:
        path.write_text(rendered, encoding="utf-8")
    elif args.output:
        Path(args.output).expanduser().resolve().write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
