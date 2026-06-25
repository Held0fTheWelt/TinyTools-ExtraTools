"""
Policy contract: **spaghetti-setup.md** is the only human-edited source
of truth.

**Derived artifact:** ``spaghetti-setup.json`` must be produced **only**
by ``setup-sync`` (MD → JSON). It is **not** a second authority; do not
hand-edit it.

**``setup-audit``** checks whether on-disk JSON still equals the
**projection** from the current Markdown (directional: stale / wrong
derived file vs canon).

**``setup-sync``** rewrites JSON from MD after validating ``M7_ref`` vs
Σ(weight×bar).

**``check --with-metrics``** optionally embeds ``metrics_bundle`` using
the derived JSON.

This module does **not** write ``spaghetti-setup.md``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import despag_hub_rel_posix, repo_root


def _repo_root() -> Path:
    """Repo root.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return repo_root()


_HUB_REL = despag_hub_rel_posix()

# Middle / first column: ``**C3**`` or inline-code `` `C3` `` (cosmetic must not break parse).
_C_MARK = r"(?:(?:\*\*C(\d)\*\*)|(?:`C(\d)`))"
_RE_BAR_ROW = re.compile(r"^\|[^|]+\|\s*" + _C_MARK + r"\s*\|\s*([^|]+?)\s*\|")
_RE_WEIGHT_ROW = re.compile(r"^\|\s*" + _C_MARK + r"\s*\|\s*([^|]+?)\s*\|")


def _c_index_from_row_match(m: re.Match[str]) -> str:
    """C index from row match.

    Args:
        m: Primary m used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    d = m.group(1) or m.group(2)
    return f"C{d}"


def _md_section(md_text: str, heading_prefix: str) -> str:
    """Slice from ``## {heading_prefix}`` (line may continue, e.g.
    ``(**M7_ref**)``) to the next ``## ``.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        md_text: Primary md text used by this step.
        heading_prefix: Primary heading prefix used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    needle = f"## {heading_prefix}"
    idx = md_text.find(needle)
    if idx < 0:
        raise ValueError(f"spaghetti-setup.md: missing section starting with {needle!r}")
    nxt = md_text.find("\n## ", idx + 1)
    if nxt >= 0:
        return md_text[idx:nxt]
    return md_text[idx:]


def parse_spaghetti_setup_md(md_text: str) -> dict[str, Any]:
    """Extract trigger_bars, weights, m7_ref from Markdown (canonical
    source).

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        md_text: Primary md text used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    bars: dict[str, float] = {}
    weights: dict[str, float] = {}
    m7_ref: float | None = None

    bars_sec = _md_section(md_text, "Per-category trigger bars")
    for line in bars_sec.splitlines():
        stripped = line.strip()
        m_bar = _RE_BAR_ROW.match(stripped)
        if not m_bar:
            continue
        ck = _c_index_from_row_match(m_bar)
        raw_val = m_bar.group(3).strip().replace("*", "").strip()
        if not raw_val:
            continue
        try:
            val = float(raw_val)
        except ValueError as e:
            raise ValueError(
                f"missing or non-numeric trigger bar for {ck} in § 'Per-category trigger bars': "
                f"{raw_val!r} (row: {stripped!r})"
            ) from e
        if ck in bars:
            raise ValueError(
                f"duplicate trigger bar row for {ck} in § 'Per-category trigger bars' "
                f"(second row: {stripped!r})"
            )
        bars[ck] = val

    w_sec = _md_section(md_text, "M7 category weights")
    for line in w_sec.splitlines():
        stripped = line.strip()
        m_w = _RE_WEIGHT_ROW.match(stripped)
        if not m_w:
            continue
        ck = _c_index_from_row_match(m_w)
        raw_w = m_w.group(3).strip().replace("*", "").strip()
        if not raw_w:
            continue
        try:
            val = float(raw_w)
        except ValueError as e:
            raise ValueError(
                f"weight for {ck} is not numeric in § 'M7 category weights': {raw_w!r} "
                f"(row: {stripped!r})"
            ) from e
        if ck in weights:
            raise ValueError(
                f"duplicate weight row for {ck} in § 'M7 category weights' (second row: {stripped!r})"
            )
        weights[ck] = val

    ref_sec = _md_section(md_text, "Composite reference")
    for line in ref_sec.splitlines():
        stripped = line.strip()
        m_ref = re.match(
            r"^\|\s*\*\*M7_ref\*\*[^|]*\|\s*(?:\*\*([\d.]+)\*\*|([\d.]+))\s*\|",
            stripped,
        )
        if m_ref:
            cell = m_ref.group(1) or m_ref.group(2)
            m7_ref = float(cell.strip())
            break

    missing_b = [f"C{i}" for i in range(1, 8) if f"C{i}" not in bars]
    missing_w = [f"C{i}" for i in range(1, 8) if f"C{i}" not in weights]
    if missing_b:
        raise ValueError(
            f"spaghetti-setup.md: missing bars for {missing_b}. In § 'Per-category trigger bars', "
            "each data row must be: | … | **Cn** | <number> | (number plain or **bold**)."
        )
    if missing_w:
        raise ValueError(
            f"spaghetti-setup.md: missing weights for {missing_w}. In § 'M7 category weights', "
            "each data row must be: | **Cn** | <number> | (number plain or **bold**)."
        )
    if m7_ref is None:
        raise ValueError(
            "spaghetti-setup.md: could not parse **M7_ref** in § 'Composite reference' "
            "(table row: | **M7_ref** … | <number> |)."
        )

    return {"trigger_bars": bars, "weights": weights, "m7_ref": m7_ref}


def compute_m7_ref(bars: dict[str, float], weights: dict[str, float]) -> float:
    """Implement ``compute_m7_ref`` for the surrounding module workflow.

    Args:
        bars: Primary bars used by this step.
        weights: Primary weights used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    return sum(float(weights[k]) * float(bars[k]) for k in (f"C{i}" for i in range(1, 8)))


SETUP_JSON_SCHEMA_VERSION = 1
SETUP_JSON_DESCRIPTION = (
    "DERIVED ONLY — regenerate with: python -m despaghettify.tools setup-sync. "
    "Do not edit by hand; spaghetti-setup.md is the sole source of truth. "
    "trigger_bars and m7_ref apply to operational anteil_pct (real %), not to "
    "ast_heuristic_v2 trigger scores."
)


def build_setup_json_document(parsed_md: dict[str, Any]) -> dict[str, Any]:
    """Machine mirror object from ``parse_spaghetti_setup_md`` result
    (ordered keys for diffs).

    The implementation iterates over intermediate items before it
    returns.

    Args:
        parsed_md: Primary parsed md used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    bars_in = parsed_md["trigger_bars"]
    weights_in = parsed_md["weights"]
    trigger_bars: dict[str, int | float] = {}
    weights: dict[str, float] = {}
    for i in range(1, 8):
        k = f"C{i}"
        b = float(bars_in[k])
        trigger_bars[k] = int(b) if b == int(b) else b
        weights[k] = float(weights_in[k])
    m7 = float(parsed_md["m7_ref"])
    m7_out = int(m7) if m7 == int(m7) else round(m7, 4)
    return {
        "schema_version": SETUP_JSON_SCHEMA_VERSION,
        "description": SETUP_JSON_DESCRIPTION,
        "trigger_bars": trigger_bars,
        "weights": weights,
        "m7_ref": m7_out,
    }


def validate_md_m7_ref_consistency(parsed_md: dict[str, Any], *, tol: float = 1e-4) -> str | None:
    """Return error message if ``M7_ref`` in the md table disagrees with
    bars×weights; else ``None``.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        parsed_md: Primary parsed md used by this step.
        tol: Primary tol used by this step.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    recomputed = compute_m7_ref(parsed_md["trigger_bars"], parsed_md["weights"])
    tab = float(parsed_md["m7_ref"])
    if abs(recomputed - tab) > tol:
        return (
            f"M7_ref in composite table is {tab} but recomputed Σ(weight_i×bar_i) is {recomputed:.6f}; "
            "fix § Composite reference and/or § Per-category trigger bars / § M7 category weights."
        )
    return None


def sync_setup_json_from_md(
    *,
    md_path: Path,
    json_path: Path,
    dry_run: bool = False,
    tol: float = 1e-4,
) -> tuple[int, list[str], dict[str, Any]]:
    """Write ``json_path`` from ``md_path`` tables.

    This callable writes or records artifacts as part of its workflow.
    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        md_path: Filesystem path to the file or directory being
            processed.
        json_path: Filesystem path to the file or directory being
            processed.
        dry_run: Whether to enable this optional behavior.
        tol: Primary tol used by this step.

    Returns:
        tuple[int, list[str], dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    msgs: list[str] = []
    try:
        md_text = md_path.read_text(encoding="utf-8")
        parsed = parse_spaghetti_setup_md(md_text)
    except (OSError, UnicodeError, ValueError) as e:
        return 2, [str(e)], {}

    err = validate_md_m7_ref_consistency(parsed, tol=tol)
    if err:
        return 2, [err], {}

    doc = build_setup_json_document(parsed)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return 0, [], doc

    json_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    json_path.write_text(text, encoding="utf-8")
    msgs.append(f"wrote {json_path.as_posix()} from {md_path.as_posix()}")
    return 0, msgs, doc


def load_setup_json(path: Path) -> dict[str, Any]:
    """Read Setup Json from configuration, disk, or remote sources.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def audit_setup(
    *,
    md_path: Path,
    json_path: Path,
    check_json_path: Path | None,
    tol: float = 1e-4,
) -> dict[str, Any]:
    """Return audit report with ``audit_status`` / ``audit_exit_code``
    (directional MD → JSON).

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        md_path: Filesystem path to the file or directory being
            processed.
        json_path: Filesystem path to the file or directory being
            processed.
        check_json_path: Filesystem path to the file or directory being
            processed.
        tol: Primary tol used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """

    def _finish(
        *,
        audit_status: str,
        audit_exit_code: int,
        parsed_md: dict[str, Any] | None,
        md_ref_recomputed: float | None,
        md_parse_errors: list[str],
        md_internal_issues: list[str],
        json_freshness_issues: list[str],
    ) -> dict[str, Any]:
        """Finish the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            audit_status: Primary audit status used by this step.
            audit_exit_code: Primary audit exit code used by this step.
            parsed_md: Primary parsed md used by this step.
            md_ref_recomputed: Primary md ref recomputed used by this
                step.
            md_parse_errors: Primary md parse errors used by this step.
            md_internal_issues: Primary md internal issues used by this
                step.
            json_freshness_issues: Primary json freshness issues used by
                this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        drift = [*md_parse_errors, *md_internal_issues, *json_freshness_issues]
        derived_ok = audit_status == "PASS"
        rep: dict[str, Any] = {
            "policy_model": "md_canonical_json_derived",
            "canonical": "spaghetti-setup.md",
            "md_path": md_path.as_posix(),
            "json_path": json_path.as_posix(),
            "audit_status": audit_status,
            "audit_exit_code": audit_exit_code,
            "md_parse_ok": parsed_md is not None,
            "md_internally_consistent": parsed_md is not None and len(md_internal_issues) == 0,
            "json_matches_md_projection": parsed_md is not None and len(json_freshness_issues) == 0,
            "parsed_md": parsed_md,
            "m7_ref_recomputed_from_md": md_ref_recomputed,
            "derived_json_matches_md": derived_ok,
            "json_mirror_ok": derived_ok,
            "md_parse_errors": md_parse_errors,
            "md_internal_issues": md_internal_issues,
            "json_freshness_issues": json_freshness_issues,
            "drift_issues": drift,
            "scan": None,
        }
        if parsed_md is None:
            return rep
        md = parsed_md
        md_ref_c = md_ref_recomputed if md_ref_recomputed is not None else compute_m7_ref(
            md["trigger_bars"], md["weights"]
        )
        rep["m7_ref_recomputed_from_md"] = round(md_ref_c, 4)
        if check_json_path and check_json_path.is_file():
            chk = json.loads(check_json_path.read_text(encoding="utf-8"))
            mb = (chk.get("metrics_bundle") or {}) if isinstance(chk, dict) else {}
            score = mb.get("score") or {}
            cats = score.get("categories") or {}
            anteil = {k: float(cats[k]["anteil_pct"]) for k in cats if k.startswith("C")}
            m7a = float(score.get("m7_anteil_pct_gewichtet") or mb.get("metric_a", {}).get("m7", 0.0))
            fires = {k: anteil[k] > md["trigger_bars"][k] for k in anteil}
            comp = m7a >= md["m7_ref"]
            rep["scan"] = {
                "anteil_pct": anteil,
                "m7_anteil_pct_gewichtet": m7a,
                "per_category_would_fire_vs_md_bars": fires,
                "composite_would_fire_vs_md_m7_ref": comp,
                "trigger_policy_would_fire": any(fires.values()) or comp,
            }
        return rep

    try:
        md_text = md_path.read_text(encoding="utf-8")
    except OSError as e:
        return _finish(
            audit_status="FAIL_MD_INVALID",
            audit_exit_code=3,
            parsed_md=None,
            md_ref_recomputed=None,
            md_parse_errors=[f"cannot read spaghetti-setup.md: {e}"],
            md_internal_issues=[],
            json_freshness_issues=[],
        )

    try:
        md = parse_spaghetti_setup_md(md_text)
    except ValueError as e:
        return _finish(
            audit_status="FAIL_MD_INVALID",
            audit_exit_code=3,
            parsed_md=None,
            md_ref_recomputed=None,
            md_parse_errors=[str(e)],
            md_internal_issues=[],
            json_freshness_issues=[],
        )

    md_ref_computed = compute_m7_ref(md["trigger_bars"], md["weights"])
    md_internal_issues: list[str] = []
    inc_msg = validate_md_m7_ref_consistency(md, tol=tol)
    if inc_msg:
        md_internal_issues.append(inc_msg)

    json_freshness_issues: list[str] = []
    try:
        js = load_setup_json(json_path)
        js_bars = {f"C{i}": float(js["trigger_bars"][f"C{i}"]) for i in range(1, 8)}
        js_w = {f"C{i}": float(js["weights"][f"C{i}"]) for i in range(1, 8)}
        js_ref = float(js["m7_ref"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        json_freshness_issues.append(
            f"cannot read or parse derived spaghetti-setup.json ({json_path}): {e} → run setup-sync"
        )
        js_bars = js_w = {}
        js_ref = float("nan")

    def _cmp_json(name: str, expected_from_md: float, in_json: float) -> None:
        """Cmp json.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            name: Primary name used by this step.
            expected_from_md: Primary expected from md used by this
                step.
            in_json: Primary in json used by this step.
        """
        if json_freshness_issues and "cannot read" in json_freshness_issues[0]:
            return
        if in_json != in_json:  # NaN
            json_freshness_issues.append(
                f"FAIL_JSON_STALE — {name}: missing or invalid value in JSON → run setup-sync"
            )
            return
        if abs(expected_from_md - in_json) > tol:
            json_freshness_issues.append(
                f"FAIL_JSON_STALE — {name}: expected from MD={expected_from_md}, on-disk JSON={in_json} "
                f"→ run: python -m despaghettify.tools setup-sync"
            )

    for k in (f"C{i}" for i in range(1, 8)):
        _cmp_json(f"trigger bar {k}", md["trigger_bars"][k], js_bars.get(k, float("nan")))
        _cmp_json(f"weight {k}", md["weights"][k], js_w.get(k, float("nan")))
    _cmp_json("m7_ref", md["m7_ref"], js_ref)

    if md_internal_issues:
        return _finish(
            audit_status="FAIL_MD_INCONSISTENT",
            audit_exit_code=2,
            parsed_md=md,
            md_ref_recomputed=md_ref_computed,
            md_parse_errors=[],
            md_internal_issues=md_internal_issues,
            json_freshness_issues=json_freshness_issues,
        )
    if json_freshness_issues:
        return _finish(
            audit_status="FAIL_JSON_STALE",
            audit_exit_code=1,
            parsed_md=md,
            md_ref_recomputed=md_ref_computed,
            md_parse_errors=[],
            md_internal_issues=[],
            json_freshness_issues=json_freshness_issues,
        )
    return _finish(
        audit_status="PASS",
        audit_exit_code=0,
        parsed_md=md,
        md_ref_recomputed=md_ref_computed,
        md_parse_errors=[],
        md_internal_issues=[],
        json_freshness_issues=[],
    )


def cmd_setup_audit(args: argparse.Namespace) -> int:
    """Implement ``cmd_setup_audit`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = _repo_root()
    md = Path(args.setup_md.strip())
    sj = Path(args.setup_json.strip())
    if not md.is_absolute():
        md = root / md
    if not sj.is_absolute():
        sj = root / sj
    cj = Path(args.check_json.strip()) if getattr(args, "check_json", "").strip() else None
    if cj and not cj.is_absolute():
        cj = root / cj

    rep = audit_setup(md_path=md, json_path=sj, check_json_path=cj)
    if getattr(args, "json", False):
        print(json.dumps(rep, indent=2))
    else:
        print("Canon (human input):", rep["canonical"], rep["md_path"])
        print("Derived artifact:", rep["json_path"])
        if rep.get("parsed_md"):
            print("M7_ref (from MD table):", rep["parsed_md"]["m7_ref"])
            print("M7_ref recomputed from MD bars×weights:", rep["m7_ref_recomputed_from_md"])
        print("Audit status:", rep.get("audit_status", "?"))
        if rep["drift_issues"]:
            print("Issues:")
            for x in rep["drift_issues"]:
                print(" ", x)
            if rep.get("audit_status") == "FAIL_JSON_STALE":
                print("Remediation: run: python -m despaghettify.tools setup-sync")
            elif rep.get("audit_status") == "FAIL_MD_INCONSISTENT":
                print("Remediation: fix § Composite reference or bar/weight tables in MD, then setup-sync.")
            elif rep.get("audit_status") == "FAIL_MD_INVALID":
                print("Remediation: fix Markdown tables (see messages above).")
        else:
            print("Audit: PASS — derived JSON matches MD projection.")
        if rep.get("scan") and rep.get("parsed_md"):
            s = rep["scan"]
            print("Scan vs md bars (Anteil %):")
            for k in sorted(s["anteil_pct"]):
                b = rep["parsed_md"]["trigger_bars"][k]
                a = s["anteil_pct"][k]
                fire = s["per_category_would_fire_vs_md_bars"][k]
                print(f"  {k}: anteil={a:.4f} bar={b} fire={fire}")
            print("  M7_anteil:", round(s["m7_anteil_pct_gewichtet"], 4), "m7_ref(md):", rep["parsed_md"]["m7_ref"])
            print("  composite fire:", s["composite_would_fire_vs_md_m7_ref"])
            print("  any policy fire:", s["trigger_policy_would_fire"])
    return int(rep.get("audit_exit_code", 1 if rep["drift_issues"] else 0))


def cmd_setup_sync(args: argparse.Namespace) -> int:
    """Implement ``cmd_setup_sync`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = _repo_root()
    md = Path(args.setup_md.strip())
    sj = Path(args.setup_json.strip())
    if not md.is_absolute():
        md = root / md
    if not sj.is_absolute():
        sj = root / sj
    dry = bool(getattr(args, "dry_run", False))
    code, msgs, doc = sync_setup_json_from_md(md_path=md, json_path=sj, dry_run=dry)
    if code != 0:
        for m in msgs:
            print(m, file=sys.stderr)
        return code
    if dry:
        print(
            f"# dry-run: would write {sj.as_posix()} from {md.as_posix()}",
            file=sys.stderr,
        )
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 0
    for m in msgs:
        print(m)
    return 0


def main_cli() -> int:
    """Implement ``main_cli`` for the surrounding module workflow.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    p = argparse.ArgumentParser(
        description="MD = canon; JSON = derived. Audit checks JSON vs MD projection; --sync writes JSON from MD.",
    )
    p.add_argument(
        "--sync",
        action="store_true",
        help="Write spaghetti-setup.json from Markdown tables (default: audit only).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="With --sync: print JSON to stdout, do not write (stderr shows target path).",
    )
    p.add_argument(
        "--setup-md",
        default=f"{_HUB_REL}/spaghetti-setup.md",
        help="Canonical policy Markdown (repo-relative ok).",
    )
    p.add_argument(
        "--setup-json",
        default=f"{_HUB_REL}/spaghetti-setup.json",
        help="Derived JSON path (repo-relative ok); do not hand-edit.",
    )
    p.add_argument(
        "--check-json",
        default="",
        help="Audit only: optional path to check --with-metrics JSON for Anteil vs md bars.",
    )
    p.add_argument("--json", action="store_true", help="Audit only: emit machine JSON report on stdout.")
    args = p.parse_args()
    if args.sync and (args.check_json.strip() or args.json):
        print("--sync is incompatible with --check-json / --json (use audit mode without --sync).", file=sys.stderr)
        return 2
    if args.sync:
        return cmd_setup_sync(args)
    return cmd_setup_audit(args)


if __name__ == "__main__":
    raise SystemExit(main_cli())
