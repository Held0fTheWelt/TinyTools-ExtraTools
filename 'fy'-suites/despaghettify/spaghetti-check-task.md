# Task: Structure / spaghetti check (reproducible)

*Path:* `despaghettify/spaghetti-check-task.md` — Overview: [README.md](README.md).

**Language:** [Repository language](../docs/dev/contributing.md#repository-language). **This task’s scope:** English for all **in-repository** prose this task maintains (input list **Latest structure scan**, **Open hotspots**, DS rows, phase notes, Mermaid labels where they carry meaning).

This task describes the **full** analysis track for the Despaghettify hub: collect **structure metrics**, name **hotspots**, maintain the canonical [input list](despaghettification_implementation_input.md) — **without** code refactors (implementation stays with the implementer and follows `[EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md)` for real waves).

**Single source of truth — split:** **Numeric** trigger policy (**C1..C7** bars, **M7** weights, derived **`M7_ref`**, composite vs scan-only **thresholds**) is **canonical** in [`spaghetti-setup.md`](spaghetti-setup.md) — edit numbers **only** there. **Procedural** rules (**Open hotspots** including **Conditions → hotspots**, binding tables, scan steps, DS row rules, Mermaid, extra checks) are **canonical in this file** only. Cursor skills and hub READMEs **route** here for procedure and to **setup** for digits; `python -m despaghettify.tools check` emits **machine metrics** (JSON). With **`--with-metrics`** (and `despaghettify/spaghetti-setup.json` present), the JSON embeds **`metrics_bundle`**: **`ast_heuristic_v2`** **`category_scores`** / **`m7`** (heuristic **Trigger v2**, advisory) plus **`score`** (**`trigger_v2`** / **`anteil_pct`**, **`m7_trigger_v2`**, **`m7_anteil_pct_gewichtet`**). **Formal gates** (`per_category_trigger_fires`, `composite_trigger_fires`, `trigger_policy_basis`: `anteil_pct`) compare **`anteil_pct`** / **`metric_a.m7`** to **bars** / **`M7_ref`** per [`spaghetti-setup.md`](spaghetti-setup.md). The input list § *Latest structure scan* shows **both** columns from **`metrics_bundle.score`** (§1).

**Scan timestamp (non-negotiable):** Any run that updates § *Latest structure scan* in the input list **must** set **As of (date & time)** to the **actual moment** the scan steps were executed (see §1 under *Maintaining the input list*).

**Threshold:** **Bars** and **`M7_ref`** apply to **`anteil_pct`** / **`metric_a.m7`** (**`M7_anteil`**), **not** to **`m7`** / **`category_scores`** (heuristic). **Update § *Information input list* …** when **`trigger_policy_fires`** is true (**any** **Anteil(C*n*) > bar*n*** **or** **`M7_anteil ≥ M7_ref`**); otherwise do **not** touch those sections — **Latest structure scan** is **always** updated (see below).

**Numeric policy (canonical):** Open [`spaghetti-setup.md`](spaghetti-setup.md) — § *Per-category trigger bars*, § *M7 category weights*, § *Composite reference (**M7_ref**)*, and the **scan-only** rule. **Do not** copy evolving bar/weight/`M7_ref` digits into this file; that would fork the policy.

**Quick read (non-authoritative summary):** per-category fire when **Anteil(C*n*) > bar_n** (strict **>**). Composite fire when **`M7_anteil ≥ M7_ref`**. Scan-only when **no** per-category fire **and** **`M7_anteil < M7_ref`** — exact numbers always from **setup**. **Trigger v2** is **not** gated by bars (advisory; see **setup** § *Heuristic trigger scale*).

## Binding sources


| Document                                                                                   | Role                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`spaghetti-setup.md`](spaghetti-setup.md)                                                                 | **Numeric** trigger policy: **C1..C7** bars, **M7** weights, **`M7_ref`**, composite vs scan-only thresholds — **edit here** when you retune conditions. |
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | **Always:** **Latest structure scan** (as-of **date and time**; **Trigger v2** + **Anteil %** for **M7** / **C1..C7** from **`metrics_bundle.score`** after **`check --with-metrics`** — same dual columns in **Score *M7*** + **AST telemetry** row under **C7**; §1); **`spaghetti_ast_scan`**; extra checks; **Open hotspots** — **prune resolved items**. **Only if trigger policy is met**: **information input list**, **recommended implementation order** (+ Mermaid §3), and the appendix § **DS-ID → primary workstream**. Keep the appendix at the bottom; do not move governance/history back above the operational scan. |
| [despaghettify/tools/spaghetti_ast_scan.py](tools/spaghetti_ast_scan.py)                              | Canonical metric run; script resolves **repo root** from its path (CWD need not be repo root).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md)                             | Analysis and Markdown maintenance create **no** new pre/post artefacts; those appear only when a **wave** with evidence runs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Local planning / issues                                                                    | Always share scan numbers; mirror proposed order / new DS rows to external tickets only after agreement — and in-repo **only** if trigger policy is met (otherwise the scan section suffices).                                                                                                                                                                                                                                                                                                                                                                                                                         |


## Do not

- Do **not** change `docs/archive/documentation-consolidation-2026/`*.
- Do **not** hand-edit **Trigger v2** / **Anteil %** / **`M7_anteil`** cells in the input list’s scan tables — copy from **`metrics_bundle.score`** (and **`metric_a.m7`**) produced by **`python -m despaghettify.tools check --with-metrics`**. Qualitative **Open hotspots** interprets; it does **not** replace machine values with ad-hoc numbers.
- Do **not** leave **resolved** items in the **Open hotspots** field of the structure scan (no stale callouts; no re-copying hotspots that the repo or a prior solve wave already fixed — see §1).
- Not a substitute for green CI: the scan is **read-side**; tests remain authoritative.

## Python AST run scope (fixed)

Always include these directories (paths relative to repository root):

- `backend/app`
- `world-engine/app`
- `ai_stack`
- `story_runtime_core`
- `tools/mcp_server`
- `administration-tool`

**Ignore:** `.state_tmp`, `site/`, `node_modules`, `.venv`, `venv`, `__pycache__` (and everything under them).

## Reproduction: AST scan script

**In repository:** [despaghettify/tools/spaghetti_ast_scan.py](tools/spaghetti_ast_scan.py) — if metric definitions change, maintain **task document and script together**.

The following block is a **copy** of the logic (if the script is missing or diverges):

```python
from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]  # repo root when this file is despaghettify/tools/spaghetti_ast_scan.py

IGNORE = (".state_tmp", "/site/", "node_modules", ".venv", "venv", "__pycache__")
ROOTS = [
    _REPO_ROOT / "backend" / "app",
    _REPO_ROOT / "world-engine" / "app",
    _REPO_ROOT / "ai_stack",
    _REPO_ROOT / "story_runtime_core",
    _REPO_ROOT / "tools" / "mcp_server",
    _REPO_ROOT / "administration-tool",
]


def walk(root: Path):
    for p in root.rglob("*.py"):
        s = p.as_posix()
        if any(x in s for x in IGNORE):
            continue
        yield p


def nest_depth(body: list[ast.stmt], d: int = 0) -> int:
    m = d
    for b in body:
        if isinstance(b, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.Try)):
            m = max(m, d + 1)
            for attr in ("body", "orelse", "handlers", "finalbody"):
                sub = getattr(b, attr, None)
                if isinstance(sub, list):
                    m = max(m, nest_depth(sub, d + 1))
    return m


def metrics(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(n, "end_lineno", None) or n.lineno
            out.append((n.name, end - n.lineno + 1, nest_depth(n.body, 0), path))
    return out


def main() -> None:
    allm = []
    for r in ROOTS:
        if r.exists():
            for p in walk(r):
                allm.extend(metrics(p))
    long50 = [x for x in allm if x[1] > 50]
    long100 = [x for x in allm if x[1] > 100]
    deep6 = [x for x in allm if x[2] >= 6]
    print("Total functions:", len(allm))
    print(">50 lines:", len(long50), ">100 lines:", len(long100), "nesting>=6:", len(deep6))
    long100.sort(key=lambda x: -x[1])
    print("Top 12 longest:")
    for name, lines, nd, p in long100[:12]:
        rel = p.relative_to(_REPO_ROOT).as_posix() if p.is_relative_to(_REPO_ROOT) else p.as_posix()
        print(f"  {lines:4d}L depth~{nd} {rel}:{name}")
    deep6.sort(key=lambda x: (-x[2], -x[1]))
    print("Top 6 nesting:")
    for name, lines, nd, p in deep6[:6]:
        rel = p.relative_to(_REPO_ROOT).as_posix() if p.is_relative_to(_REPO_ROOT) else p.as_posix()
        print(f"  depth {nd} {lines:4d}L {rel}:{name}")
    ate = _REPO_ROOT / "backend" / "app" / "runtime" / "ai_turn_executor.py"
    if ate.exists():
        raw = len(ate.read_text(encoding="utf-8", errors="replace").splitlines())
        ex = [x for x in metrics(ate) if x[0] == "execute_turn_with_ai"]
        print("ai_turn_executor.py lines:", raw)
        if ex:
            print("execute_turn_with_ai:", ex[0][1], "lines depth~", ex[0][2])


if __name__ == "__main__":
    main()
```

Invoke (the in-repo script resolves **repo root** from `__file__`; **CWD** need not be the repo root):

```bash
python "./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"
```

The same AST logic (plus `ds005` and greps) is available as JSON via `python -m despaghettify.tools check` (see [`superpowers/references/CLI.md`](superpowers/references/CLI.md)). For **C1..C7** and **M7** Richtwerte in Markdown, run **`python -m despaghettify.tools check --with-metrics`** so the payload includes **`metrics_bundle`** (requires **`despaghettify/spaghetti-setup.json`**, the **derived** policy file from **`spaghetti-setup.md`** via **`setup-sync`**).

## Extra checks (fixed)

1. **Duplicate builtins:** search for `def build_god_of_carnage_solo` in `**/builtins.py` (backend + world-engine) — mention state briefly in the scan table while builtins/drift remains an open theme.
2. **Import workarounds (spot check):** grep under `backend/app/runtime` for `TYPE_CHECKING`, `avoid circular`, `circular dependency` — qualitative only (“still present” / “fewer hits”); no full graph analysis required.

## Maintaining the input list

All in [despaghettification_implementation_input.md](despaghettification_implementation_input.md). The trigger policy is defined numerically in [`spaghetti-setup.md`](spaghetti-setup.md) (per-category bars **plus** composite **`M7 ≥ M7_ref`**); the input list mirrors the same rules under § *Trigger policy for check task updates*.

### 1) Latest structure scan — **always**

- **As of (date & time) — required:** Fill the **As of (date & time)** cell with the **timestamp when this check run’s scan commands ran** (not a hand-waved day only). Use `**YYYY-MM-DD HH:mm:ss`** (24-hour). **Timezone:** optional; add **once** in parentheses after the time if it matters (e.g. `(Europe/Berlin)` or `(UTC)`). If the repo assumes one zone everywhere, a single sentence in the input list header is enough and the cell may omit the suffix.
- **Metrics — machine Richtwerte (zwei Spalten):** In der **Haupt**-Scan-Tabelle und in **Score *M7*** jeweils **zwei** numerische Spalten: (1) **Trigger v2** — aus **`metrics_bundle.score.categories.Cn.trigger_v2`** / **`m7_trigger_v2`** (gleich **`category_scores`** / **`m7`**); zwei Dezimalstellen; **kein** Balkenvergleich. (2) **Anteil %** — aus **`anteil_pct`** / **`m7_anteil_pct_gewichtet`**; **dieselbe** Spalte vs. **`trigger_bars`** / **`M7_ref`** in **`spaghetti-setup.json`** (**`trigger_policy_basis`:** `anteil_pct`). **Gleiche** Zahlen in Haupttabelle und **Score *M7***-Tabelle. **Do not** invent numbers “by feel”.
- **AST telemetry:** In the **main** § *Latest structure scan* table, keep the row **AST telemetry N / L₅₀ / L₁₀₀ / D₆** with the four **counts** from `python "./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"` (not **%**).
- **Cross-section consistency:** Any § *Active progress* row in [despaghettification_implementation_input.md](despaghettification_implementation_input.md) that describes the **same** spaghetti-check run as § *Latest structure scan* must use the **identical** **N / L₅₀ / L₁₀₀ / D₆** (copy from that scan table in the **same** edit). Finished check passes: append to [despaghettification_completed_log.md](despaghettification_completed_log.md) and clear § *Active progress*. Do not retype counts from an older terminal buffer or a prior scan — that is how log and scan drift apart.
- **Score *M7* subsection:** Tabelle **Symbol | Meaning | Trigger v2 | Anteil %** (plus oberste **M7**-Zeile mit beiden Summen). Unter **C7** eine Zeile **AST telemetry**: **Trigger**-Spalte **—**, **Anteil**-Spalte dieselben vier **Zählwerte** wie in der Haupttabelle. **Do not** duplicate telemetry in the trigger-policy table; **do not** add a separate mini-table or filler comments in cells.
- **Extra checks** (builtins, runtime spot check `TYPE_CHECKING` / cycle hints) briefly in the scan section if you run them.
- Longest functions and top nesting **fully** only in **script output**; in Markdown **core findings** and the **Open hotspots** table row as follows:
  - **Open hotspots must not show solved problems.** Before writing, read the previous **Open hotspots** text and reconcile with the **current** repo and this run’s script output (line counts, paths, names). If a named function or theme is **no longer** a top offender or was **split / moved / shortened** by an implemented wave, **drop** that fragment from **Open hotspots**; use **—** when nothing structural remains to call out beyond the numeric row.
  - Only list **still-open** structural issues (typically 2–5 short clauses aligned with current top lines / nesting or checks). Do **not** reintroduce text that [spaghetti-solve-task.md](spaghetti-solve-task.md) already cleared unless the problem has **regressed** in the tree.
  - Do **not** duplicate the full script leaderboard in **Open hotspots** — that belongs in terminal output only; the cell is for **curated, unresolved** callouts.
  - **Conditions → hotspots (mandatory):** Nach dem Eintragen der Spalten **`Anteil %`** mit [`spaghetti-setup.md`](spaghetti-setup.md) abgleichen (**strict >** je Balken; Komposit **`M7_anteil ≥ M7_ref`**). **Open hotspots** müssen jede **feuernde** Policy-Bedingung (Anteil-basiert) verankern; **Trigger v2** optional zur Einordnung zitieren. **Scan-only**, wenn **keine** Anteil-Überschreitung **und** **`M7_anteil < M7_ref`**.

### 2) Information input list (table) — **only if trigger policy is met**

- Each recognised or worsened **structure / spaghetti gap** gets its **own row** with columns: **ID**, **pattern**, **location**, **hint / measurement idea**, **direction** (one-sentence sketch), **collision hint** (what would be risky in parallel).
- **Pattern column:** Begin **pattern** with the **M7 category symbol(s)** this wave primarily addresses — **C1** … **C7** as in [`spaghetti-setup.md`](spaghetti-setup.md) § *Per-category trigger bars* (same names as § *Latest structure scan* / input list triggers). Use **C3 ·** then a short free-text hook; if several categories apply, **C2 · C3 ·** then the hook. Pick symbols from the current scan story (length, nesting, cycles, duplication, etc.), not arbitrary tags.
- **IDs:** **update** existing **DS-*** rows (measurements, location, collision) instead of inventing duplicates; assign the next free **DS-*** number only for **new** topics.
- Then maintain the **DS-ID → primary workstream** table in the same document’s bottom appendix (slug → `artifacts/workstreams/<slug>/pre|post/` per [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)). The check must update that table in place; it must not move the appendix or governance block above § *Latest structure scan*.
- **If trigger policy is not met:** do **not** change this section or the workstream table within the spaghetti check.

### 3) Recommended implementation order — **only if trigger policy is met**

- Section **“Recommended implementation order”** as the analysis agent’s **proposal**: table **priority / phase**, **DS-ID(s)**, **short logic**, **workstream (primary)**, **note** (dependencies, gates).
- **Mermaid (mandatory when phases are filled):** If the phase table still contains only placeholders (`—`), **omit** the diagram until a pass fills real rows. Once **any** phase row has real **DS-ID(s)**, immediately **below** the table include a **fenced** `mermaid` code block (` ```mermaid` … ` ``` `) with a **`flowchart`** or **`graph`** that reflects the **same** sequencing **and parallelism** as the table:
  - **Node labels (readability + compatibility):** **one source line per node**, shape **`id["label"]`**. Put **phase · DS-ID · very short hook** in `label`, parts separated by **` · `** (U+00B7 middle dot, spaces around it). Example: `P1["1 · DS-010 · AI turn"]`. **Do not** break labels across multiple lines in the repo file, **do not** use `\n`, `<br/>`, or inner backtick “markdown string” wrappers in hub diagrams — different viewers disagree on those, and the result is often worse than one dense line.
  - **Edges:** draw a **hard** dependency as a single arrow. For **parallel** work (independent DS phases after a common predecessor, separate workstreams, no import conflict), use a **fork** (`Predecessor --> A` and `Predecessor --> B`) and a **join** (`A --> Merge`, `B --> Merge`) when a later phase truly requires both; if independence is documented but no join is needed, fork only and end branches on leaf phases.
  - **Linear fallback:** use a simple chain **only** when every phase is strictly sequential or soft-ordered with no credible parallel band.
  - **Do not** omit the diagram when non-placeholder phase rows exist — keep syntax valid for MkDocs / GitHub Mermaid.
- **Heuristic (order):** interfaces and shared edges (**DTOs, clear module boundaries**) before large moves; **high coupling / deep nesting hotspots** not in parallel by two owners without aligned artefact sets; do not hide builtins/import topics behind large runtime refactors when the scan surfaces them first.
- If only numbers change without a new substantive thesis: **confirm** the phase table or add a row **“no change vs last scan”** — do not leave empty placeholder phases when the input table has rows; **still refresh** the Mermaid if the phase table row text or order changed.
- **If trigger policy is not met:** do **not** change this section within the spaghetti check (no phase shuffle for scan noise only).

**How to build a *suitable* phase table (required whenever DS rows are filled):**

1. **Cover every open DS-ID** from § *Information input list* with at least one **phase** row (unless two IDs are explicitly merged into one wave with team agreement — then one row may list multiple **DS-*** and the note must say so). **Never** leave the phase table as `—` while the DS table has real rows. Each **DS-*** row’s **pattern** must already carry the **C1..C7** prefix rule from §2.
2. **Order phases by risk and blast radius**, not by DS number: prefer topics that **stabilise shared runtime / import seams** (turn pipeline, narrative commit, `app.runtime` edges, `ds005`-visible modules) **before** very large **service orchestration** functions that pull many imports. Put **package-separated** hotspots (e.g. `ai_stack` only) in a **later** phase unless the scan shows they block backend work.
3. **One primary workstream per phase row** (see [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)): it must match where **pre/post** artefacts would go for that wave. If a phase touches two packages, pick the **primary** workstream and mention the other in **note** (“call sites only”, “no separate pre/post”).
4. **Short logic** = one line: *what* this phase achieves structurally (e.g. “shrink X before refactoring Y”). **Note** = concrete **gates**: which `pytest` paths, `ds005`, or integration checks the implementer should run after the slice.
5. **Dependencies:** if phase B genuinely requires interfaces from phase A, say so in **note** on phase B; avoid claiming a hard dependency unless imports or tests prove it — default is **soft ordering** (risk reduction), which is still valid to document as “prefer A before B”.
6. **Parallelism / independence:** explicitly ask which DS phases could run **in parallel** (different **primary workstream**, no shared hot files, no hard import coupling). When credible, use **parallel phase bands** in the table (e.g. `3a` / `3b` with **Parallel** in **note**, or two rows sharing the same priority with an explicit **parallel** sentence) instead of a fake linear order. Call out **collision** risks if two “parallel” tasks still touch the same module surface. The Mermaid must **show** forks/joins consistent with those notes.
7. **Mermaid:** after the table, add or update the **mandatory** diagram; **single-line** `["…"]` labels (§3) and edges must stay in sync with the **priority / phase** and **DS-ID(s)** columns and with **parallel** vs **hard** dependencies above.

### Optional

- **Active progress**, [despaghettification_completed_log.md](despaghettification_completed_log.md), and `WORKSTREAM_*_STATE.md`: primary use is a **formal wave** with pre/post (see governance). **If** a check pass is logged, reuse § *Latest structure scan* **AST telemetry** and **`metrics_bundle`** **M7** / **C1..C7** verbatim in the log row — the scan section is the **single source of truth** for those numbers in that pass; then move finished rows to the completed log.

## Output format for the requester (short)

After the run: **3–8 sentences** on **`M7_anteil` vs `M7_ref`**, per-category **Anteil** vs bars, **Trigger v2** outliers (advisory), and **Open hotspots**. Confirm **Open hotspots** covers **every** firing **Anteil**-based condition. **Only if trigger policy is met**: add **1–3 sentences** on implementation order, parallelism, **Mermaid**, and changed sections. If trigger policy is not met: **Latest structure scan** (+ pruned hotspots) only.

## Counterpart: implementation wave by wave

The **execution track** (one **DS-ID** per invocation, e.g. `run spaghetti-solve-task DS-016`; sub-waves with pre/post until that **DS-ID** is closed in the input list): [spaghetti-solve-task.md](spaghetti-solve-task.md).
