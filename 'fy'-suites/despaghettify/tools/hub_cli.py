#!/usr/bin/env python3
"""Hub cli for despaghettify.tools.

"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from fy_platform.core.manifest import load_manifest, suite_config
from despaghettify.tools.repo_paths import despag_hub_dir, despag_hub_rel_posix, repo_root

ROOT = Path.cwd()
HUB = Path(__file__).resolve().parents[1]
HUB_REL = HUB.name
INPUT_LIST = HUB / "despaghettification_implementation_input.md"
RUNTIME_DIR = ROOT / "backend" / "app" / "runtime"
DESPAG_TOOLS_DIR = HUB / "tools"

# Information input list table: open rows use | **DS-nnn** |
OPEN_DS_ROW = re.compile(r"^\|\s*\*\*(DS-\d+)\*\*\s*\|")
# Closed history rows in the same table
CLOSED_DS_ROW = re.compile(r"^\|\s*~~(DS-\d+)~~")
BACKTICK_CHUNK = re.compile(r"`([^`]{1,400})`")
# Distinct gate-like tokens (lowercase keys for counting)
_GATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pytest", re.compile(r"\bpytest\b", re.I)),
    ("ds005", re.compile(r"\bds005\b", re.I)),
    ("ruff", re.compile(r"\bruff\b", re.I)),
    ("mypy", re.compile(r"\bmypy\b", re.I)),
    ("mkdocs", re.compile(r"\bmkdocs\b", re.I)),
    ("npm", re.compile(r"\bnpm\b", re.I)),
    ("cargo", re.compile(r"\bcargo\b", re.I)),
    ("pre_commit", re.compile(r"pre-commit|pre_commit", re.I)),
)


_LAST_ARCHIVE_SYNC: dict | None = None


def _run_archive_sync() -> dict | None:
    """Move closed DS rows from the input list into the completed log (idempotent)."""
    import os

    if os.environ.get("DESPAG_SKIP_ARCHIVE_SYNC", "").strip().lower() in ("1", "true", "yes"):
        return None
    from despaghettify.tools.input_list_archive import sync_input_archive  # noqa: PLC0415

    global _LAST_ARCHIVE_SYNC
    try:
        result = sync_input_archive(HUB)
    except OSError as exc:
        _LAST_ARCHIVE_SYNC = {"error": str(exc), "changed": False}
        print(f"despaghettify: archive sync failed: {exc}", file=sys.stderr)
        return _LAST_ARCHIVE_SYNC
    payload = {
        "changed": result.changed,
        "archived_ds": list(result.archived_ds),
        "archived_active_rows": result.archived_active_rows,
        "message": result.message,
    }
    _LAST_ARCHIVE_SYNC = payload
    if result.changed:
        print(f"despaghettify: {result.message}", file=sys.stderr)
    return payload


def _ensure_repo_root() -> None:
    """Ensure repo root.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    global ROOT, HUB, HUB_REL, INPUT_LIST, RUNTIME_DIR, DESPAG_TOOLS_DIR
    # Protect the critical _ensure_repo_root work so failures can be turned into a
    # controlled result or cleanup path.
    try:
        ROOT = repo_root()
        HUB = despag_hub_dir(ROOT)
        HUB_REL = despag_hub_rel_posix(ROOT)
    except RuntimeError:
        # Keep import resilient for non-WoS layouts; checks below gate invalid contexts.
        ROOT = Path.cwd()
        HUB = Path(__file__).resolve().parents[1]
        HUB_REL = HUB.name
    # Read and normalize the input data before _ensure_repo_root branches on or
    # transforms it further.
    INPUT_LIST = HUB / "despaghettification_implementation_input.md"
    DESPAG_TOOLS_DIR = HUB / "tools"
    manifest, _warnings = load_manifest(ROOT)
    cfg = suite_config(manifest, "despaghettify")
    runtime_rel = str(cfg.get("runtime_dir", "")).strip() if cfg else ""
    RUNTIME_DIR = (ROOT / runtime_rel).resolve() if runtime_rel else (ROOT / "backend" / "app" / "runtime")
    # Branch on not HUB.is_dir() so _ensure_repo_root only continues along the matching
    # state path.
    if not HUB.is_dir():
        print(
            "Despaghettify hub directory not found (expected under 'fy'-suites/despaghettify/). "
            "Use ``pip install -e .`` from repo root or set PYTHONPATH to the parent of the ``despaghettify`` package; "
            "see 'fy'-suites/despaghettify/README.md.",
            file=sys.stderr,
        )
        raise SystemExit(3)


def _load_input_list_text() -> str:
    """Load input list text.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if not INPUT_LIST.is_file():
        print(f"Missing {INPUT_LIST.relative_to(ROOT)}", file=sys.stderr)
        raise SystemExit(3)
    return INPUT_LIST.read_text(encoding="utf-8", errors="replace")


def _information_input_section(md: str) -> str:
    """Information input section.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        md: Primary md used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    start = md.find("## Information input list")
    end = md.find("## Recommended implementation order")
    if start == -1 or end == -1 or end <= start:
        print("Could not slice Information input list section.", file=sys.stderr)
        raise SystemExit(3)
    return md[start:end]


def _preflight_input_bundle(override_path: str | None) -> tuple[str, Path]:
    """Return (markdown, path_shown_in_json).

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        override_path: Filesystem path to the file or directory being
            processed.

    Returns:
        tuple[str, Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    if not override_path or not override_path.strip():
        return _load_input_list_text(), INPUT_LIST
    p = Path(override_path.strip())
    if not p.is_absolute():
        p = ROOT / p
    fixtures = (HUB / "tools" / "fixtures").resolve()
    try:
        p.resolve().relative_to(fixtures)
    except ValueError:
        print(
            f"solve-preflight: --override-input-list must resolve under {HUB_REL}/tools/fixtures/",
            file=sys.stderr,
        )
        raise SystemExit(3)
    if not p.is_file():
        print(f"Not a file: {p}", file=sys.stderr)
        raise SystemExit(3)
    return p.read_text(encoding="utf-8", errors="replace"), p


def cmd_open_ds(_args: argparse.Namespace) -> int:
    """Implement ``cmd_open_ds`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        _args: Primary args used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools.input_list_archive import open_ds_ids_from_md  # noqa: PLC0415

    md = _load_input_list_text()
    for line in open_ds_ids_from_md(md):
        print(line)
    return 0


def _parse_md_table_row_cells(line: str) -> list[str]:
    """Parse md table row cells.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        line: 1-based source line number used by the audit or edit step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    line = line.strip()
    if not (line.startswith("|") and line.endswith("|")):
        return []
    inner = line[1:-1]
    return [c.strip() for c in inner.split("|")]


def _path_like_backticks(text: str) -> list[str]:
    """Path like backticks.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    for m in BACKTICK_CHUNK.finditer(text):
        chunk = m.group(1).strip()
        for piece in re.split(r",\s*", chunk):
            p = piece.strip()
            if not p:
                continue
            if "/" not in p and not p.endswith(".py") and not p.endswith(".ts"):
                continue
            tok = p.split("(")[0].strip()
            tok = tok.split()[0] if tok else ""
            if tok and tok not in seen:
                seen.add(tok)
                ordered.append(tok)
    return ordered


def _gate_keywords_in_text(text: str) -> list[str]:
    """Gate keywords in text.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    found: list[str] = []
    for name, pat in _GATE_PATTERNS:
        if pat.search(text) and name not in found:
            found.append(name)
    return found


def _wave_sizing_heuristic(row_line: str) -> dict:
    """Rough, machine-printed hints — agents still choose honest N from the
    DS row.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        row_line: 1-based source line number used by the audit or edit
            step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    cells = _parse_md_table_row_cells(row_line)
    focus = row_line
    if len(cells) >= 5:
        focus = " | ".join(cells[2:6])
    paths = _path_like_backticks(row_line)
    gates = _gate_keywords_in_text(row_line)
    ast_signal = 1 if re.search(r"\bAST\b", focus) else 0
    effort = min(8, len(paths)) + len(gates) + ast_signal
    if effort <= 1:
        n_min, n_max = 1, 2
    elif effort == 2:
        n_min, n_max = 1, 3
    elif effort <= 4:
        n_min, n_max = 2, 4
    elif effort <= 6:
        n_min, n_max = 3, 6
    else:
        n_min, n_max = 4, 8
    split_ds_recommended = effort >= 8
    return {
        "effort_score": effort,
        "path_signals": paths[:20],
        "path_signal_count": len(paths),
        "gate_keywords": gates,
        "ast_column_signal": bool(ast_signal),
        "n_suggested_min": n_min,
        "n_suggested_max": n_max,
        "split_ds_recommended": split_ds_recommended,
        "note": "Heuristic only; choose N from DS direction and governance. If honest N > 8, split DS rows per solve task.",
    }


def validate_wave_plan_document(
    data: object,
    *,
    repo_root: Path | None = None,
    check_primary_paths: bool = False,
    gate_prefix_allowlist: tuple[str, ...] | None = None,
) -> tuple[bool, list[str]]:
    """Return (ok, errors). Optional strict checks for CI or pre-merge.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        data: Primary data used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        check_primary_paths: Whether to enable this optional behavior.
        gate_prefix_allowlist: Primary gate prefix allowlist used by
            this step.

    Returns:
        tuple[bool, list[str]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    errs: list[str] = []
    if not isinstance(data, dict):
        return False, ["root must be a JSON object"]
    ver = data.get("schema_version")
    if ver != "1" and ver != 1:
        errs.append('schema_version must be 1 (JSON number) or "1" (string)')
    raw_ds = data.get("ds_id")
    if not isinstance(raw_ds, str) or not re.fullmatch(r"(?i)DS-\d+", raw_ds.strip()):
        errs.append("ds_id must be a string matching DS-<digits> (e.g. DS-016)")
    slug = data.get("slug", None)
    if slug is not None and (not isinstance(slug, str) or not str(slug).strip()):
        errs.append("slug, when present, must be a non-empty string")
    session_date = data.get("session_date", None)
    if session_date is not None and (not isinstance(session_date, str) or not session_date.strip()):
        errs.append("session_date, when present, must be a non-empty string")
    waves = data.get("sub_waves")
    if not isinstance(waves, list) or len(waves) < 1:
        errs.append("sub_waves must be a non-empty array")
        return False, errs
    if len(waves) > 8:
        errs.append("sub_waves length > 8 violates solve-task policy; split DS rows")
    for i, w in enumerate(waves):
        prefix = f"sub_waves[{i}]"
        if not isinstance(w, dict):
            errs.append(f"{prefix} must be an object")
            continue
        idx = w.get("index")
        if not isinstance(idx, int) or idx < 1:
            errs.append(f"{prefix}.index must be int >= 1")
        wid = w.get("id")
        if not isinstance(wid, str) or not wid.strip():
            errs.append(f"{prefix}.id must be a non-empty string (e.g. w01)")
        goal = w.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            errs.append(f"{prefix}.goal must be a non-empty string")
        gates = w.get("gate_commands")
        if not isinstance(gates, list) or len(gates) < 1:
            errs.append(f"{prefix}.gate_commands must be a non-empty array of strings")
        else:
            for j, g in enumerate(gates):
                if not isinstance(g, str) or not g.strip():
                    errs.append(f"{prefix}.gate_commands[{j}] must be a non-empty string")
        pp = w.get("primary_paths")
        if pp is None:
            pass
        elif not isinstance(pp, list):
            errs.append(f"{prefix}.primary_paths must be an array when present")
        else:
            for j, p in enumerate(pp):
                if not isinstance(p, str) or not p.strip():
                    errs.append(f"{prefix}.primary_paths[{j}] must be a non-empty string")
    dict_waves = [w for w in waves if isinstance(w, dict)]
    if len(dict_waves) == len(waves) and not errs:
        indices = [w.get("index") for w in dict_waves]
        if all(isinstance(i, int) for i in indices) and sorted(indices) != list(
            range(1, len(waves) + 1)
        ):
            errs.append("sub_waves[].index must be 1..N with no gaps or duplicates")

    if not errs:
        cw = data.get("completed_wave_ids")
        if cw is not None:
            if not isinstance(cw, list) or not all(isinstance(x, str) and x.strip() for x in cw):
                errs.append("completed_wave_ids must be an array of non-empty strings when present")
            else:
                ids_in_waves = {w.get("id") for w in dict_waves if isinstance(w.get("id"), str)}
                for c in cw:
                    if c.strip() not in ids_in_waves:
                        errs.append(
                            f"completed_wave_ids entry {c.strip()!r} is not a sub_wave.id "
                            f"(known: {sorted(ids_in_waves)})"
                        )
        ni = data.get("next_index")
        if ni is not None:
            if not isinstance(ni, int) or ni < 1 or ni > len(waves) + 1:
                errs.append(
                    f"next_index must be int in 1..{len(waves) + 1} when present "
                    "(use N+1 when all waves are done)"
                )

    if not errs and gate_prefix_allowlist:
        prefixes = tuple(p.strip() for p in gate_prefix_allowlist if p.strip())
        if prefixes:
            for i, w in enumerate(dict_waves):
                gates = w.get("gate_commands") if isinstance(w, dict) else None
                if not isinstance(gates, list):
                    continue
                for j, g in enumerate(gates):
                    if not isinstance(g, str) or not g.strip():
                        continue
                    g2 = g.strip()
                    if not any(g2.startswith(p) for p in prefixes):
                        errs.append(
                            f"sub_waves[{i}].gate_commands[{j}] must start with one of {prefixes!r} "
                            "(--gate-prefix-allowlist)"
                        )

    if not errs and check_primary_paths:
        base = repo_root or ROOT
        base = base.resolve()
        for i, w in enumerate(dict_waves):
            pplist = w.get("primary_paths") if isinstance(w, dict) else None
            if not isinstance(pplist, list):
                continue
            for j, rel in enumerate(pplist):
                if not isinstance(rel, str) or not rel.strip():
                    continue
                target = (base / rel).resolve()
                try:
                    target.relative_to(base)
                except ValueError:
                    errs.append(f"sub_waves[{i}].primary_paths[{j}] escapes repo_root: {rel}")
                    continue
                if not target.exists():
                    errs.append(f"sub_waves[{i}].primary_paths[{j}] not found under repo: {rel}")

    return len(errs) == 0, errs


def cmd_wave_plan_validate(args: argparse.Namespace) -> int:
    """Implement ``cmd_wave_plan_validate`` for the surrounding module
    workflow.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    path = Path(args.file)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        return 3
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, json.JSONDecodeError) as e:
        print(str(e), file=sys.stderr)
        return 3
    allow = tuple(
        p.strip()
        for p in (args.gate_prefix_allowlist or "").split(",")
        if p.strip()
    )
    allow_t: tuple[str, ...] | None = allow if allow else None
    ok, errors = validate_wave_plan_document(
        data,
        repo_root=ROOT,
        check_primary_paths=bool(args.check_primary_paths),
        gate_prefix_allowlist=allow_t,
    )
    if ok:
        print(json.dumps({"ok": True, "file": path.relative_to(ROOT).as_posix()}, indent=2))
        return 0
    print(json.dumps({"ok": False, "errors": errors}, indent=2), file=sys.stderr)
    return 2


def cmd_solve_preflight(args: argparse.Namespace) -> int:
    """Implement ``cmd_solve_preflight`` for the surrounding module
    workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    raw = (args.ds or "").strip()
    m = re.fullmatch(r"(?i)DS-(\d+)", raw)
    if not m:
        print("Use --ds DS-016 (form DS-<digits>).", file=sys.stderr)
        return 3
    ds_id = f"DS-{m.group(1)}"

    md, list_src = _preflight_input_bundle((args.override_input_list or "").strip() or None)
    section = _information_input_section(md)
    open_hit = False
    closed_hit = False
    row_line: str | None = None
    for line in section.splitlines():
        if f"~~{ds_id}~~" in line:
            closed_hit = True
        om = OPEN_DS_ROW.match(line)
        if om and om.group(1) == ds_id:
            open_hit = True
            row_line = line

    if open_hit:
        wave_sizing = _wave_sizing_heuristic(row_line) if row_line else {}
        print(
            json.dumps(
                {
                    "ds_id": ds_id,
                    "status": "open",
                    "input_list": list_src.relative_to(ROOT).as_posix(),
                    "wave_sizing": wave_sizing,
                },
                indent=2,
            )
        )
        return 0
    if closed_hit:
        print(
            json.dumps(
                {
                    "ds_id": ds_id,
                    "status": "closed",
                    "message": "row struck through / CLOSED in Information input list",
                },
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "ds_id": ds_id,
                "status": "missing",
                "message": "no **DS-** open row in Information input list section",
            },
            indent=2,
        )
    )
    return 2


def _grep_runtime_cycle_hints() -> dict:
    """Grep runtime cycle hints.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    patterns = ("TYPE_CHECKING", "avoid circular", "circular dependency")
    hits: list[dict] = []
    if not RUNTIME_DIR.is_dir():
        return {"runtime_dir_exists": False, "hit_count": 0, "hits": []}
    for path in sorted(RUNTIME_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            lower = line.lower()
            if any(p.lower() in lower for p in patterns):
                hits.append({"path": path.relative_to(ROOT).as_posix(), "line": i, "snippet": line.strip()[:200]})
    return {"runtime_dir_exists": True, "hit_count": len(hits), "hits": hits[:50]}


def _grep_builtins_goc_def() -> dict:
    """Match spaghetti-check extra check: def build_god_of_carnage_solo in
    **/builtins.py.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    needle = "def build_god_of_carnage_solo"
    matches: list[str] = []
    for root in (ROOT / "backend", ROOT / "world-engine"):
        if not root.is_dir():
            continue
        for path in root.rglob("builtins.py"):
            try:
                txt = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if needle in txt:
                matches.append(path.relative_to(ROOT).as_posix())
    goc_template = ROOT / "story_runtime_core" / "goc_solo_builtin_template.py"
    template_has = goc_template.is_file() and needle in goc_template.read_text(
        encoding="utf-8", errors="replace"
    )
    return {
        "def_in_builtins_py_paths": matches,
        "count_in_builtins_py": len(matches),
        "goc_solo_builtin_template_has_def": template_has,
    }


def cmd_check(args: argparse.Namespace) -> int:
    """Implement ``cmd_check`` for the surrounding module workflow.

    This callable writes or records artifacts as part of its workflow.
    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    sys.path.insert(0, str(DESPAG_TOOLS_DIR))
    import spaghetti_ast_scan as sas  # noqa: PLC0415

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ast_stats = sas.collect_ast_stats()
    runtime_import_gate_enabled = RUNTIME_DIR.is_dir()
    ds005_lines: list[str] = []
    ds005_exit = 0
    ds005_stderr = ""
    if runtime_import_gate_enabled:
        ds005 = subprocess.run(
            [sys.executable, str(DESPAG_TOOLS_DIR / "ds005_runtime_import_check.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        ds005_lines = [ln for ln in (ds005.stdout or "").splitlines() if ln.strip()]
        ds005_exit = ds005.returncode
        ds005_stderr = ds005.stderr or ""
    if _LAST_ARCHIVE_SYNC is not None:
        archive_sync = _LAST_ARCHIVE_SYNC
    else:
        archive_sync = _run_archive_sync()
    report: dict = {
        "kind": "despaghettify_check",
        "generated_at_utc": ts,
        "repo_root": ROOT.as_posix(),
        "archive_sync": archive_sync,
        "ast": ast_stats,
        "ds005": {
            "enabled": runtime_import_gate_enabled,
            "exit_code": ds005_exit,
            "import_ok_count": len([ln for ln in ds005_lines if ln.startswith("import_ok")]),
            "stdout_tail": ds005_lines[-5:] if ds005_lines else [],
        },
        "extra_builtins_goc": _grep_builtins_goc_def(),
        "extra_runtime_grep": _grep_runtime_cycle_hints(),
    }
    if getattr(args, "with_metrics", False):
        setup_path = HUB / "spaghetti-setup.json"
        if setup_path.is_file():
            try:
                from despaghettify.tools.metrics_bundle import build_metrics_bundle  # noqa: PLC0415

                setup = json.loads(setup_path.read_text(encoding="utf-8"))
                report["metrics_bundle"] = build_metrics_bundle(
                    check_payload=report,
                    setup=setup,
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                pass
    text = json.dumps(report, indent=2)
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out_path.write_text(text + "\n", encoding="utf-8")
        print(str(out_path.relative_to(ROOT)))
    else:
        print(text)
    if ds005_exit != 0:
        print(ds005_stderr, file=sys.stderr)
        return 1
    return 0


def cmd_autonomous_init(args: argparse.Namespace) -> int:
    """Implement ``cmd_autonomous_init`` for the surrounding module
    workflow.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import autonomous_loop as al  # noqa: PLC0415

    code, msg, _state = al.init_session(force=bool(args.force))
    if code != 0:
        print(msg, file=sys.stderr)
    else:
        print(msg)
    return code


def cmd_autonomous_advance(args: argparse.Namespace) -> int:
    """Implement ``cmd_autonomous_advance`` for the surrounding module
    workflow.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import autonomous_loop as al  # noqa: PLC0415

    kind = args.kind.strip().lower().replace("-", "_")
    if kind not in ("backlog_implement", "backlog_solve", "main_check", "main_solve"):
        print("kind must be backlog-implement | backlog-solve | main-check | main-solve", file=sys.stderr)
        return 2
    res = al.advance(
        kind,  # type: ignore[arg-type]
        ds=args.ds.strip() if args.ds else None,
        check_json=args.check_json.strip() if args.check_json else None,
    )
    print(res.message)
    if not res.ok:
        print(res.message, file=sys.stderr)
    return res.exit_code


def cmd_autonomous_status(_args: argparse.Namespace) -> int:
    """Implement ``cmd_autonomous_status`` for the surrounding module
    workflow.

    Args:
        _args: Primary args used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import autonomous_loop as al  # noqa: PLC0415

    print(json.dumps(al.status_json(), indent=2))
    return 0


def cmd_autonomous_verify(args: argparse.Namespace) -> int:
    """Implement ``cmd_autonomous_verify`` for the surrounding module
    workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import autonomous_loop as al  # noqa: PLC0415

    setup = Path(args.setup_json.strip()) if args.setup_json.strip() else None
    if setup and not setup.is_absolute():
        setup = ROOT / setup
    code, msgs = al.verify(allow_dirty=bool(args.allow_dirty), setup_json=setup)
    for m in msgs:
        print(m)
    return code


def cmd_metrics_emit(args: argparse.Namespace) -> int:
    """Implement ``cmd_metrics_emit`` for the surrounding module workflow.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools.metrics_bundle import emit_metrics_bundle  # noqa: PLC0415

    cj = Path(args.check_json.strip())
    sj = Path(args.setup_json.strip())
    if not cj.is_absolute():
        cj = ROOT / cj
    if not sj.is_absolute():
        sj = ROOT / sj
    bundle = emit_metrics_bundle(check_json_path=cj, setup_json_path=sj)
    text = json.dumps(bundle, indent=2)
    if args.out.strip():
        out = Path(args.out.strip())
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out.write_text(text + "\n", encoding="utf-8")
        print(str(out.relative_to(ROOT)))
    else:
        print(text)
    return 0


def cmd_setup_audit(args: argparse.Namespace) -> int:
    """Implement ``cmd_setup_audit`` for the surrounding module workflow.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import spaghetti_setup_audit as ssa  # noqa: PLC0415

    return ssa.cmd_setup_audit(args)


def cmd_setup_sync(args: argparse.Namespace) -> int:
    """Implement ``cmd_setup_sync`` for the surrounding module workflow.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools import spaghetti_setup_audit as ssa  # noqa: PLC0415

    return ssa.cmd_setup_sync(args)


def cmd_trigger_eval(args: argparse.Namespace) -> int:
    """Implement ``cmd_trigger_eval`` for the surrounding module workflow.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    _ensure_repo_root()
    from despaghettify.tools.metrics_bundle import emit_metrics_bundle  # noqa: PLC0415

    cj = Path(args.check_json.strip())
    sj = Path(args.setup_json.strip())
    if not cj.is_absolute():
        cj = ROOT / cj
    if not sj.is_absolute():
        sj = ROOT / sj
    bundle = emit_metrics_bundle(check_json_path=cj, setup_json_path=sj)
    out = {
        "fires": bundle["trigger_policy_fires"],
        "per_category_trigger_fires": bundle["per_category_trigger_fires"],
        "trigger_policy_basis": bundle.get("trigger_policy_basis", "anteil_pct"),
        "m7": bundle["m7"],
        "m7_anteil_pct_gewichtet": bundle["metric_a"]["m7"],
        "m7_ref": bundle["m7_ref"],
        "category_scores": bundle["category_scores"],
        "source": bundle.get("source"),
    }
    print(json.dumps(out, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Implement ``main`` for the surrounding module workflow.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Resolve repo + hub before any ``default=f\"{HUB_REL}/…\"`` argparse wiring: at import time
    # ``HUB_REL`` is only the basename (``despaghettify``); after this call it is the repo-relative
    # POSIX path (``'fy'-suites/despaghettify``) so defaults point at real files on CI.
    _ensure_repo_root()
    parser = argparse.ArgumentParser(description="Despaghettify hub automation CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Run AST scan, ds005, extra greps; print JSON (and optional --out).")
    p_check.add_argument("--out", type=str, default="", help="Write JSON report to this path (under repo if relative).")
    p_check.add_argument(
        "--with-metrics",
        action="store_true",
        help=f"If {HUB_REL}/spaghetti-setup.json exists, embed metrics_bundle (heuristic v2) in the JSON output.",
    )
    p_check.set_defaults(func=cmd_check)

    p_pf = sub.add_parser("solve-preflight", help="Verify DS-id is open in Information input list.")
    p_pf.add_argument("--ds", required=True, help="e.g. DS-016")
    p_pf.add_argument(
        "--override-input-list",
        default="",
        metavar="PATH",
        help=f"CI/test only: markdown under {HUB_REL}/tools/fixtures/ with § Information input list "
        "(must contain ## Information input list … ## Recommended implementation order).",
    )
    p_pf.set_defaults(func=cmd_solve_preflight)

    p_wpv = sub.add_parser(
        "wave-plan-validate",
        help="Validate a wave_plan.json against the despaghettify schema (exit 2 on validation errors).",
    )
    p_wpv.add_argument("--file", required=True, help="Path to wave_plan JSON (repo-relative or absolute).")
    p_wpv.add_argument(
        "--check-primary-paths",
        action="store_true",
        help="Require each sub_wave.primary_paths entry to exist under repo root (optional strict check).",
    )
    p_wpv.add_argument(
        "--gate-prefix-allowlist",
        default="",
        help="Comma-separated command prefixes; if set, each gate_command must start with one of them.",
    )
    p_wpv.set_defaults(func=cmd_wave_plan_validate)

    p_list = sub.add_parser("open-ds", help="Print open DS-ids (bold rows) from Information input list.")
    p_list.set_defaults(func=cmd_open_ds)

    p_ai = sub.add_parser(
        "autonomous-init",
        help=f"Create {HUB_REL}/state/artifacts/autonomous_loop/autonomous_state.json (exit 2 if exists without --force).",
    )
    p_ai.add_argument("--force", action="store_true", help="Overwrite existing autonomous session state.")
    p_ai.set_defaults(func=cmd_autonomous_init)

    p_aa = sub.add_parser(
        "autonomous-advance",
        help="Legal transition for autonomous loop (exit 2 on rule violation). Kinds: backlog-implement, backlog-solve, main-check, main-solve.",
    )
    p_aa.add_argument(
        "--kind",
        required=True,
        help="backlog-implement | backlog-solve | main-check | main-solve",
    )
    p_aa.add_argument("--ds", default="", help="Required for backlog-* and main-solve, e.g. DS-016")
    p_aa.add_argument(
        "--check-json",
        default="",
        help="Required for backlog-implement; optional for main-check (repo-relative path to hub check JSON).",
    )
    p_aa.set_defaults(func=cmd_autonomous_advance)

    p_as = sub.add_parser("autonomous-status", help="Print JSON session status and next hints.")
    p_as.set_defaults(func=cmd_autonomous_status)

    p_av = sub.add_parser(
        "autonomous-verify",
        help="Verify autonomous_state vs open-ds, optional HEAD, dirty tree; exit 1 advisory stall, 2 hard fail.",
    )
    p_av.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow git dirty worktree outside ignored prefixes.",
    )
    p_av.add_argument(
        "--setup-json",
        default="",
        metavar="PATH",
        help="Optional spaghetti-setup.json for trigger_eval line in output.",
    )
    p_av.set_defaults(func=cmd_autonomous_verify)

    p_me = sub.add_parser(
        "metrics-emit",
        help="Emit metrics_bundle JSON from check JSON + spaghetti-setup.json (heuristic v2).",
    )
    p_me.add_argument("--check-json", required=True, help="Path to check --out JSON (repo-relative ok).")
    p_me.add_argument(
        "--setup-json",
        default=f"{HUB_REL}/spaghetti-setup.json",
        help="Path to spaghetti-setup.json mirror.",
    )
    p_me.add_argument("--out", default="", help="Write bundle to this path (repo-relative ok).")
    p_me.set_defaults(func=cmd_metrics_emit)

    p_te = sub.add_parser(
        "trigger-eval",
        help="Print trigger policy evaluation from check JSON + spaghetti-setup.json.",
    )
    p_te.add_argument("--check-json", required=True, help="Path to check --out JSON.")
    p_te.add_argument(
        "--setup-json",
        default=f"{HUB_REL}/spaghetti-setup.json",
        help="Path to spaghetti-setup.json mirror.",
    )
    p_te.set_defaults(func=cmd_trigger_eval)

    p_sa = sub.add_parser(
        "setup-audit",
        help="Verify derived spaghetti-setup.json matches projection from canonical spaghetti-setup.md.",
    )
    p_sa.add_argument(
        "--setup-md",
        default=f"{HUB_REL}/spaghetti-setup.md",
        help="Canonical policy Markdown — sole source of truth (repo-relative ok).",
    )
    p_sa.add_argument(
        "--setup-json",
        default=f"{HUB_REL}/spaghetti-setup.json",
        help="Derived JSON only (repo-relative ok); regenerate with setup-sync, do not hand-edit.",
    )
    p_sa.add_argument(
        "--check-json",
        default="",
        help="Optional check --with-metrics JSON: Anteil %% vs bars from MD canon.",
    )
    p_sa.add_argument("--json", action="store_true", help="Emit JSON report on stdout.")
    p_sa.set_defaults(func=cmd_setup_audit)

    p_sy = sub.add_parser(
        "setup-sync",
        help="Regenerate derived spaghetti-setup.json from canonical spaghetti-setup.md (MD → JSON only).",
    )
    p_sy.add_argument(
        "--setup-md",
        default=f"{HUB_REL}/spaghetti-setup.md",
        help="Canonical policy Markdown — sole source of truth (repo-relative ok).",
    )
    p_sy.add_argument(
        "--setup-json",
        default=f"{HUB_REL}/spaghetti-setup.json",
        help="Derived JSON output path (repo-relative ok); overwrites prior projection.",
    )
    p_sy.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON to stdout only; stderr shows target path (no write).",
    )
    p_sy.set_defaults(func=cmd_setup_sync)

    p_arch = sub.add_parser(
        "sync-archive",
        help="Archive closed DS rows from the input list into despaghettification_completed_log.md.",
    )
    p_arch.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing files.",
    )
    p_arch.set_defaults(func=cmd_sync_archive)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command != "sync-archive":
        _run_archive_sync()
    return int(args.func(args))


def cmd_sync_archive(args: argparse.Namespace) -> int:
    """Run archive sync explicitly (also runs automatically before other subcommands)."""
    import json

    _ensure_repo_root()
    from despaghettify.tools.input_list_archive import sync_input_archive  # noqa: PLC0415

    result = sync_input_archive(HUB, dry_run=bool(args.dry_run))
    print(
        json.dumps(
            {
                "changed": result.changed,
                "archived_ds": result.archived_ds,
                "archived_active_rows": result.archived_active_rows,
                "message": result.message,
                "input_list": result.input_path,
                "completed_log": result.completed_path,
                "dry_run": bool(args.dry_run),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
