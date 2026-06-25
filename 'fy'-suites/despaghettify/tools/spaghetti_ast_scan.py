"""
AST metrics for structure / spaghetti reviews. See
``'fy'-suites/despaghettify/spaghetti-check-task.md``.

Paths are resolved via ``repo_root()`` so the process **current working
directory** need not be the repo root.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from collections import Counter
from pathlib import Path

from fy_platform.core.manifest import load_manifest, roots_for_suite

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import repo_root

try:
    _REPO_ROOT = repo_root()
except RuntimeError:
    _REPO_ROOT = Path.cwd()


def _resolve_roots() -> list[Path]:
    """Resolve roots.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    # Read and normalize the input data before _resolve_roots branches on or transforms
    # it further.
    manifest, _warnings = load_manifest(_REPO_ROOT)
    configured = roots_for_suite(manifest=manifest, suite_name="despaghettify", key="scan_roots")
    # Branch on configured so _resolve_roots only continues along the matching state
    # path.
    if configured:
        return [(_REPO_ROOT / rel).resolve() for rel in configured]
    return [
        _REPO_ROOT / "backend" / "app",
        _REPO_ROOT / "world-engine" / "app",
        _REPO_ROOT / "ai_stack",
        _REPO_ROOT / "story_runtime_core",
        _REPO_ROOT / "tools" / "mcp_server",
        _REPO_ROOT / "administration-tool",
    ]

_MAGIC_INT_SKIP = frozenset({0, 1, 2, -1})


def _repo_rel(p: Path) -> str:
    """Repo rel.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        p: Primary p used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    try:
        return p.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


IGNORE = (".state_tmp", "/site/", "node_modules", ".venv", "venv", "__pycache__")
ROOTS = _resolve_roots()


def walk(root: Path):
    """Yield successive values while streaming ``Walk``.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
    """
    for p in root.rglob("*.py"):
        s = p.as_posix()
        if any(x in s for x in IGNORE):
            continue
        yield p


def nest_depth(body: list[ast.stmt], d: int = 0) -> int:
    """Implement ``nest_depth`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        body: Primary body used by this step.
        d: Primary d used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    m = d
    for b in body:
        if isinstance(b, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.Try)):
            m = max(m, d + 1)
            for attr in ("body", "orelse", "handlers", "finalbody"):
                sub = getattr(b, attr, None)
                if isinstance(sub, list):
                    m = max(m, nest_depth(sub, d + 1))
    return m


def _magic_int_literal_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Heuristic: int ``ast.Constant`` in function body excluding tiny
    sentinels.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        node: Parsed AST object being inspected or transformed.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    c = 0
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and type(sub.value) is int:
            if sub.value in _MAGIC_INT_SKIP:
                continue
            c += 1
    return c


def metrics(path: Path):
    """Implement ``metrics`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(n, "end_lineno", None) or n.lineno
            out.append(
                (
                    n.name,
                    end - n.lineno + 1,
                    nest_depth(n.body, 0),
                    path,
                    _magic_int_literal_count(n),
                )
            )
    return out


def _count_python_files() -> int:
    """Count python files.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    n = 0
    for r in ROOTS:
        if r.exists():
            for _ in walk(r):
                n += 1
    return n


def collect_ast_stats() -> dict:
    """Programmatic metrics for despaghettify.tools.hub_cli and CI (same
    logic as main()).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    allm: list = []
    for r in ROOTS:
        if r.exists():
            for p in walk(r):
                allm.extend(metrics(p))
    long50 = [x for x in allm if x[1] > 50]
    long100 = [x for x in allm if x[1] > 100]
    deep6 = [x for x in allm if x[2] >= 6]
    deep5 = [x for x in allm if x[2] >= 5]
    deep4 = [x for x in allm if x[2] >= 4]
    deep3 = [x for x in allm if x[2] >= 3]
    name_counts = Counter(x[0] for x in allm)
    dup_name_funcs = sum(1 for x in allm if name_counts[x[0]] > 1)
    magic_ge_5 = sum(1 for x in allm if x[4] >= 5)
    control_heavy = sum(1 for x in allm if x[2] >= 3 or x[1] > 80)
    long100.sort(key=lambda x: -x[1])
    deep6.sort(key=lambda x: (-x[2], -x[1]))
    top12 = [
        {"name": name, "lines": lines, "nest_depth": nd, "path": _repo_rel(p)}
        for name, lines, nd, p, _magic in long100[:12]
    ]
    top6n = [
        {"name": name, "lines": lines, "nest_depth": nd, "path": _repo_rel(p)}
        for name, lines, nd, p, _magic in deep6[:6]
    ]
    ate = _REPO_ROOT / "backend" / "app" / "runtime" / "ai_turn_executor.py"
    ai_turn_extra: dict | None = None
    if ate.exists():
        raw_lines = len(ate.read_text(encoding="utf-8", errors="replace").splitlines())
        ex = [x for x in metrics(ate) if x[0] == "execute_turn_with_ai"]
        ai_turn_extra = {
            "file_lines": raw_lines,
            "execute_turn_with_ai": (
                {"lines": ex[0][1], "nest_depth": ex[0][2]} if ex else None
            ),
        }
    _ics_path = Path(__file__).resolve().parent / "import_cycle_share.py"
    _spec = importlib.util.spec_from_file_location("_despag_import_cycle_share", _ics_path)
    _ics = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_ics)
    c1m = _ics.backend_app_cycle_file_share(_REPO_ROOT)
    return {
        "total_functions": len(allm),
        "total_python_files": _count_python_files(),
        "count_over_50_lines": len(long50),
        "count_over_100_lines": len(long100),
        "count_nesting_ge_3": len(deep3),
        "count_nesting_ge_4": len(deep4),
        "count_nesting_ge_5": len(deep5),
        "count_nesting_ge_6": len(deep6),
        "count_functions_magic_int_literals_ge_5": magic_ge_5,
        "count_functions_duplicate_name_across_files": dup_name_funcs,
        "count_functions_control_flow_heavy": control_heavy,
        "c1_files_in_import_cycles_pct": c1m["c1_files_in_import_cycles_pct"],
        "c1_import_graph_files": c1m["c1_graph_files"],
        "c1_files_in_cycles": c1m["c1_files_in_cycles"],
        "top12_longest": top12,
        "top6_nesting": top6n,
        "ai_turn_executor": ai_turn_extra,
    }


def main() -> None:
    """Implement ``main`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.
    """
    stats = collect_ast_stats()
    allm_n = stats["total_functions"]
    long50_n = stats["count_over_50_lines"]
    long100_n = stats["count_over_100_lines"]
    deep6_n = stats["count_nesting_ge_6"]
    print("Total functions:", allm_n)
    print(">50 lines:", long50_n, ">100 lines:", long100_n, "nesting>=6:", deep6_n)
    print("Top 12 longest:")
    for row in stats["top12_longest"]:
        print(
            f"  {row['lines']:4d}L depth~{row['nest_depth']} {row['path']}:{row['name']}"
        )
    print("Top 6 nesting:")
    for row in stats["top6_nesting"]:
        print(
            f"  depth {row['nest_depth']} {row['lines']:4d}L {row['path']}:{row['name']}"
        )
    extra = stats.get("ai_turn_executor")
    if extra:
        print("ai_turn_executor.py lines:", extra["file_lines"])
        if extra.get("execute_turn_with_ai"):
            et = extra["execute_turn_with_ai"]
            print("execute_turn_with_ai:", et["lines"], "lines depth~", et["nest_depth"])


if __name__ == "__main__":
    main()
