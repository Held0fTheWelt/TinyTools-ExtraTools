"""
Deterministic metrics_bundle from AST check payload +
spaghetti-setup.json.

**Heuristik (Trigger v2):** ``category_scores`` / ``m7`` =
``ast_heuristic_v2`` (0…100, **beratend** / Trend — **keine**
Balkenvergleiche mehr).

**Trigger-Policy (hart):** ``per_category_trigger_fires`` und
``composite_trigger_fires`` vergleichen **``condition_shares_pct``**
(``metric_a.category_scores`` / ``score.*.anteil_pct``) und
``metric_a.m7`` (**``m7_anteil_pct_gewichtet``**) mit ``trigger_bars`` /
``M7_ref`` aus der **abgeleiteten** ``spaghetti-setup.json`` (Projektion
der MD-Policy; **echte %-Anteile**, siehe ``spaghetti-setup.md``).

**v2 vs v1:** Category scores use **saturating curves**
``100*(1-exp(-…))`` with a numeric **ceiling below 100** so routine
repos never show misleading **100%** spaghetti on proxy metrics. **C4**
uses **L₅₀ density** (per total function); **C6** uses **L₁₀₀ density**
— decoupled from C4. **C1** remains a weak cycle proxy until a real
cycle metric exists.

**Lesbare Anteile (``literal_rates`` + ``plain_language_de``):** Neben
``category_scores`` (Heuristik) liefert ``literal_rates`` u. a.
**`condition_shares_pct`**: **sieben echte Anteile** (operational
definiert, siehe Sätze in ``plain_language_de``). **C1** nutzt
**Dateien** unter ``backend/app`` (Importgraph nur Kanten
``app``/``app.*`` v1), **C2–C7** nutzen **Funktionen** / gemessene
Funktionsmenge als Nenner — in ``plain_language_de`` erklärt. Balken
gelten für diese Anteile, **nicht** für ``category_scores``.

**Score (``score``):** Beim ``check --with-metrics`` immer mit
ausgeliefert: nebeneinander **``trigger_v2``** (Heuristik v2, 0…100,
**kein** Behaupten „das ist ein gemessener %-Anteil“) und
**``anteil_pct``** (echte %-Anteile wie ``condition_shares_pct``).
Aggregat: **``m7_trigger_v2``** vs. **``m7_anteil_pct_gewichtet``**
(gleiche **weights** wie Trigger-``m7``).

**Metrik A (``metric_a``):** Gewichtete **Anteil-%-**Summe — **dieselbe
Größe** wie die **Trigger-Policy**-Kompositprüfung
(**``m7_anteil_pct_gewichtet``** vs. ``M7_ref``).
``metric_a.category_scores`` = ``condition_shares_pct``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# Scores are on a 0..100 *interpretation* scale but never claim exact 100 for
# finite AST inputs (avoids "totally spaghetti" misreadings).
_SCORE_CAP = 99.99


def _exp_pressure(intensity: float) -> float:
    """Map non-negative intensity to [0, _SCORE_CAP); rises quickly then
    eases.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        intensity: Primary intensity used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    # Branch on intensity <= 0.0 so _exp_pressure only continues along the matching
    # state path.
    if intensity <= 0.0:
        return 0.0
    return min(_SCORE_CAP, 100.0 * (1.0 - math.exp(-intensity)))


def ast_heuristic_category_scores(ast: dict[str, Any]) -> dict[str, float]:
    """Map collect_ast_stats() shape to C1..C7 on 0..100 scale (v2
    heuristics).

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        ast: Primary ast used by this step.

    Returns:
        dict[str, float]:
            Structured payload describing the outcome of the
            operation.
    """
    n_raw = int(ast.get("total_functions") or 0)
    long100 = int(ast.get("count_over_100_lines") or 0)
    long50 = int(ast.get("count_over_50_lines") or 0)
    d6 = int(ast.get("count_nesting_ge_6") or 0)

    if n_raw <= 0:
        # No function corpus: avoid fake denominators or a non-zero C1 floor.
        return {"C1": 0.0, "C2": 0.0, "C3": 0.0, "C4": 0.0, "C5": 0.0, "C6": 0.0, "C7": 0.0}

    n = float(n_raw)
    ratio50 = long50 / n
    ratio100 = long100 / n

    # C3: very long functions — count-based pressure (similar mid-range to v1).
    c3 = _exp_pressure(long100 / 32.0)
    # C2: deep nesting instances — soft saturation on count.
    c2 = _exp_pressure(d6 / 25.0)
    # C4: breadth of >50-line callables vs codebase size (not raw count alone).
    c4 = _exp_pressure(18.0 * ratio50)
    # C6: "heavy tail" share — >100-line callables vs size (decoupled from C4).
    c6 = _exp_pressure(40.0 * ratio100)
    # C1: weak proxy until cycle metric exists (only when n_raw > 0).
    c1 = min(_SCORE_CAP, 5.0 + (long100 / 250.0) * 8.0)
    c5 = min(_SCORE_CAP, c4 * 0.55)
    c7 = min(_SCORE_CAP, max(c2, c3) * 0.65)
    return {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5, "C6": c6, "C7": c7}


def weighted_m7(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Implement ``weighted_m7`` for the surrounding module workflow.

    Args:
        scores: Primary scores used by this step.
        weights: Primary weights used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    return sum(float(scores[k]) * float(weights[k]) for k in scores if k in weights)


def condition_shares_pct(ast: dict[str, Any]) -> dict[str, float]:
    """Seven operational **true %** shares (0..100). C1 = file % under
    ``backend/app``; C2–C7 = function %.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        ast: Primary ast used by this step.

    Returns:
        dict[str, float]:
            Structured payload describing the outcome of the
            operation.
    """
    n_raw = int(ast.get("total_functions") or 0)
    c1 = float(ast.get("c1_files_in_import_cycles_pct") or 0.0)
    ng4 = int(ast.get("count_nesting_ge_4") or 0)
    long100 = int(ast.get("count_over_100_lines") or 0)
    long50 = int(ast.get("count_over_50_lines") or 0)
    mag = int(ast.get("count_functions_magic_int_literals_ge_5") or 0)
    dup = int(ast.get("count_functions_duplicate_name_across_files") or 0)
    ctrl = int(ast.get("count_functions_control_flow_heavy") or 0)

    def pct(count: int) -> float:
        """Pct the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            count: Primary count used by this step.

        Returns:
            float:
                Value produced by this callable as
                ``float``.
        """
        if n_raw <= 0:
            return 0.0
        return round(100.0 * float(count) / float(n_raw), 4)

    return {
        "C1": round(c1, 4),
        "C2": pct(ng4),
        "C3": pct(long100),
        "C4": pct(long50),
        "C5": pct(mag),
        "C6": pct(dup),
        "C7": pct(ctrl),
    }


def literal_rates_from_ast(ast: dict[str, Any]) -> dict[str, Any]:
    """Legacy density keys plus ``condition_shares_pct`` (seven true
    shares).

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        ast: Primary ast used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    n_raw = int(ast.get("total_functions") or 0)
    long100 = int(ast.get("count_over_100_lines") or 0)
    long50 = int(ast.get("count_over_50_lines") or 0)
    d6 = int(ast.get("count_nesting_ge_6") or 0)
    if n_raw <= 0:
        over_100 = over_50 = nest_ge_6 = 0.0
    else:
        fn = float(n_raw)
        over_100 = 100.0 * long100 / fn
        over_50 = 100.0 * long50 / fn
        nest_ge_6 = 100.0 * d6 / fn
    over_100_among_over_50 = (100.0 * long100 / float(long50)) if long50 else 0.0
    cond = condition_shares_pct(ast)
    return {
        "total_functions_measured": n_raw,
        "total_python_files_measured": int(ast.get("total_python_files") or 0),
        "functions_over_100_lines_pct": round(over_100, 4),
        "functions_over_50_lines_pct": round(over_50, 4),
        "functions_nesting_ge_6_pct": round(nest_ge_6, 4),
        "over_100_lines_among_over_50_lines_pct": round(over_100_among_over_50, 4),
        "condition_shares_pct": cond,
        "c1_import_graph_files": int(ast.get("c1_import_graph_files") or 0),
        "c1_files_in_cycles": int(ast.get("c1_files_in_cycles") or 0),
    }


def category_scores_metric_a(*, literal: dict[str, Any]) -> dict[str, float]:
    """Same keys as ``category_scores`` — values from
    ``condition_shares_pct``.

    Args:
        literal: Primary literal used by this step.

    Returns:
        dict[str, float]:
            Structured payload describing the outcome of the
            operation.
    """
    return {k: float(literal["condition_shares_pct"][k]) for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")}


def score_trigger_vs_anteil(
    *,
    category_scores_trigger_v2: dict[str, float],
    anteile_pct: dict[str, float],
    m7_trigger_v2: float,
    m7_anteil_pct_gewichtet: float,
) -> dict[str, Any]:
    """Human-oriented pairing: v2 trigger scale vs true %-shares (``check
    --with-metrics``).

    The implementation iterates over intermediate items before it
    returns.

    Args:
        category_scores_trigger_v2: Primary category scores trigger v2
            used by this step.
        anteile_pct: Primary anteile pct used by this step.
        m7_trigger_v2: Primary m7 trigger v2 used by this step.
        m7_anteil_pct_gewichtet: Primary m7 anteil pct gewichtet used by
            this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    cats: dict[str, dict[str, float]] = {}
    for ck in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
        cats[ck] = {
            "trigger_v2": round(float(category_scores_trigger_v2[ck]), 4),
            "anteil_pct": round(float(anteile_pct[ck]), 4),
        }
    return {
        "legend_de": (
            "``trigger_v2`` = Heuristik v2 (0…100, saturierend); **kein** Balkenvergleich, "
            "nur beratend. ``anteil_pct`` = operationaler Mess-Anteil in % "
            "(``literal_rates.condition_shares_pct``); **Balken** / ``M7_ref`` aus "
            "``spaghetti-setup`` gelten **nur** hier. **C1** = Prozent der Dateien unter "
            "``backend/app`` im Importgraph; **C2–C7** = Prozent der gemessenen Funktionen. "
            "``m7_trigger_v2`` / ``m7_anteil_pct_gewichtet``: gleiche ``weights``."
        ),
        "categories": cats,
        "m7_trigger_v2": round(float(m7_trigger_v2), 4),
        "m7_anteil_pct_gewichtet": round(float(m7_anteil_pct_gewichtet), 4),
    }


def plain_language_de(*, literal: dict[str, Any]) -> dict[str, str]:
    """One German sentence per category matching ``condition_shares_pct``
    definitions.

    Args:
        literal: Primary literal used by this step.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    n = int(literal["total_functions_measured"])
    gf = int(literal.get("c1_import_graph_files") or 0)
    cyc = int(literal.get("c1_files_in_cycles") or 0)
    s = literal["condition_shares_pct"]
    c1 = float(s["C1"])
    c2 = float(s["C2"])
    c3 = float(s["C3"])
    c4 = float(s["C4"])
    c5 = float(s["C5"])
    c6 = float(s["C6"])
    c7 = float(s["C7"])
    return {
        "C1": (
            f"Anteil der {gf} analysierten Python-Dateien unter ``backend/app``, die in einem "
            f"Importzyklus liegen (nur explizite ``app.*``-Kanten, v1): {c1:.2f} % "
            f"({cyc} Dateien)."
        ),
        "C2": (
            f"Anteil der {n} gemessenen Funktionen mit AST-Verschachtelungstiefe ≥ 4: {c2:.2f} %."
        ),
        "C3": (f"Anteil der {n} gemessenen Funktionen mit mehr als 100 AST-Zeilen: {c3:.2f} %."),
        "C4": (f"Anteil der {n} gemessenen Funktionen mit mehr als 50 AST-Zeilen: {c4:.2f} %."),
        "C5": (
            f"Anteil der {n} gemessenen Funktionen mit ≥ 5 nicht-trivialen int-Literalen im Body "
            f"(Heuristik, ohne globalen Modulzustand): {c5:.2f} %."
        ),
        "C6": (
            f"Anteil der {n} gemessenen Funktionen, deren Name in mehreren Dateien vorkommt "
            f"(schwacher Duplikat-/Namenskollisions-Proxy): {c6:.2f} %."
        ),
        "C7": (
            f"Anteil der {n} gemessenen Funktionen mit Verschachtelung ≥ 3 **oder** "
            f"mehr als 80 AST-Zeilen (Kontrollfluss-/Lesbarkeits-Proxy): {c7:.2f} %."
        ),
    }


def m7_ref_from_setup(setup: dict[str, Any]) -> float:
    """Implement ``m7_ref_from_setup`` for the surrounding module workflow.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        setup: Primary setup used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    if "m7_ref" in setup:
        return float(setup["m7_ref"])
    bars = setup["trigger_bars"]
    w = setup["weights"]
    return sum(float(w[f"C{i}"]) * float(bars[f"C{i}"]) for i in range(1, 8))


def build_metrics_bundle(*, check_payload: dict[str, Any], setup: dict[str, Any]) -> dict[str, Any]:
    """Construct a new Metrics Bundle instance or graph.

    Args:
        check_payload: Primary check payload used by this step.
        setup: Primary setup used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    ast = check_payload.get("ast") or {}
    scores = ast_heuristic_category_scores(ast)
    literal = literal_rates_from_ast(ast)
    weights = {f"C{i}": float(setup["weights"][f"C{i}"]) for i in range(1, 8)}
    bars = {f"C{i}": float(setup["trigger_bars"][f"C{i}"]) for i in range(1, 8)}
    m7 = weighted_m7(scores, weights)
    m7_ref = m7_ref_from_setup(setup)
    shares = category_scores_metric_a(literal=literal)
    m7_metric_a = weighted_m7(shares, weights)
    # Bars and M7_ref are defined on operational %-shares, not on heuristic trigger_v2.
    per_fire = {k: float(shares[k]) > bars[k] for k in shares}
    composite_fire = m7_metric_a >= m7_ref
    fires = any(per_fire.values()) or composite_fire
    score = score_trigger_vs_anteil(
        category_scores_trigger_v2=scores,
        anteile_pct=shares,
        m7_trigger_v2=m7,
        m7_anteil_pct_gewichtet=m7_metric_a,
    )
    return {
        "kind": "metrics_bundle",
        "schema_version": 1,
        "source": "ast_heuristic_v2",
        "category_scores": scores,
        "score": score,
        "literal_rates": literal,
        "plain_language_de": plain_language_de(literal=literal),
        "metric_a": {
            "id": "share_weighted_m7",
            "description_de": (
                "Gewichtetes Mittel der ``condition_shares_pct``; **Trigger-Policy**-Komposit "
                "(Vergleich mit ``M7_ref`` / Balken für **Anteil %**, nicht für ``m7`` Trigger)."
            ),
            "category_scores": shares,
            "m7": round(m7_metric_a, 4),
        },
        "m7": round(m7, 4),
        "m7_ref": round(m7_ref, 4),
        "trigger_policy_basis": "anteil_pct",
        "trigger_bars": bars,
        "weights": weights,
        "per_category_trigger_fires": per_fire,
        "composite_trigger_fires": composite_fire,
        "trigger_policy_fires": fires,
    }


def emit_metrics_bundle(*, check_json_path: Path, setup_json_path: Path) -> dict[str, Any]:
    """Implement ``emit_metrics_bundle`` for the surrounding module
    workflow.

    Args:
        check_json_path: Filesystem path to the file or directory being
            processed.
        setup_json_path: Filesystem path to the file or directory being
            processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    check_payload = _load_json(check_json_path)
    setup = _load_json(setup_json_path)
    return build_metrics_bundle(check_payload=check_payload, setup=setup)


def _load_json(path: Path) -> dict[str, Any]:
    """Load json.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return json.loads(path.read_text(encoding="utf-8"))
