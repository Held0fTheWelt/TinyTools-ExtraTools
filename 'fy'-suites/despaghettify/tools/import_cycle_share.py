"""
Static import-cycle share under ``backend/app`` (``app.*`` imports only,
v1).

Used for a **literal %** of Python files that participate in a
non-trivial strongly connected component of the **file-level** import
graph. Relative imports and non-``app`` packages are ignored in v1
(documented limitation).
"""
from __future__ import annotations

import ast
from pathlib import Path


def _walk_py(root: Path) -> list[Path]:
    """Walk py.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    ignore = (".state_tmp", "/site/", "node_modules", ".venv", "venv", "__pycache__")
    out: list[Path] = []
    # Branch on not root.is_dir() so _walk_py only continues along the matching state
    # path.
    if not root.is_dir():
        return out
    # Process p one item at a time so _walk_py applies the same rule across the full
    # collection.
    for p in root.rglob("*.py"):
        s = p.as_posix()
        # Branch on any((x in s for x in ignore)) so _walk_py only continues along the
        # matching state path.
        if any(x in s for x in ignore):
            continue
        out.append(p.resolve())
    return sorted(out)


def _resolve_app_module(repo_root: Path, module: str) -> Path | None:
    """Resolve app module.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        module: Primary module used by this step.

    Returns:
        Path | None:
            Filesystem path produced or resolved by this
            callable.
    """
    if module == "app":
        init = repo_root / "backend" / "app" / "__init__.py"
        return init if init.is_file() else None
    if not module.startswith("app."):
        return None
    tail = module[4:].replace(".", "/")
    base = repo_root / "backend" / "app"
    py = base / f"{tail}.py"
    if py.is_file():
        return py.resolve()
    init = base / tail / "__init__.py"
    if init.is_file():
        return init.resolve()
    return None


def _absolute_app_targets(tree: ast.AST) -> list[str]:
    """Absolute app targets.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        tree: Parsed AST object being inspected or transformed.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "app" or name.startswith("app."):
                    mods.append(name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "app" or node.module.startswith("app."):
                mods.append(node.module)
    return mods


def backend_app_cycle_file_share(repo_root: Path) -> dict[str, float | int]:
    """Return ``c1_files_in_import_cycles_pct`` and counts for
    ``backend/app``.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, float | int]:
            Structured payload describing the outcome of the
            operation.
    """
    base = repo_root / "backend" / "app"
    paths = _walk_py(base)
    n = len(paths)
    if n == 0:
        return {"c1_files_in_import_cycles_pct": 0.0, "c1_graph_files": 0, "c1_files_in_cycles": 0}
    idx: dict[Path, int] = {p: i for i, p in enumerate(paths)}
    edges: list[list[int]] = [[] for _ in range(n)]
    for i, p in enumerate(paths):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        seen: set[int] = set()
        for mod in _absolute_app_targets(tree):
            tgt = _resolve_app_module(repo_root, mod)
            if tgt is None or tgt not in idx:
                continue
            j = idx[tgt]
            if j not in seen:
                seen.add(j)
                edges[i].append(j)

    on_cycle = _tarjan_cycle_nodes(n, edges)
    k = int(on_cycle.count(True))
    return {
        "c1_files_in_import_cycles_pct": round(100.0 * k / float(n), 4),
        "c1_graph_files": n,
        "c1_files_in_cycles": k,
    }


def _tarjan_cycle_nodes(n: int, edges: list[list[int]]) -> list[bool]:
    """True for vertices that belong to an SCC of size > 1 or a self-loop.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        n: Primary n used by this step.
        edges: Primary edges used by this step.

    Returns:
        list[bool]:
            Collection produced from the parsed or
            accumulated input data.
    """
    index = 0
    indices = [-1] * n
    lowlink = [-1] * n
    stack: list[int] = []
    onstack = [False] * n
    in_cycle = [False] * n

    def strongconnect(v: int) -> None:
        """Implement ``strongconnect`` for the surrounding module workflow.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            v: Primary v used by this step.
        """
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        onstack[v] = True
        for w in edges[v]:
            if indices[w] == -1:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif onstack[w]:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp: list[int] = []
            while True:
                w = stack.pop()
                onstack[w] = False
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                for x in comp:
                    in_cycle[x] = True
            elif v in edges[v]:
                in_cycle[v] = True

    for v in range(n):
        if indices[v] == -1:
            strongconnect(v)
    return in_cycle
