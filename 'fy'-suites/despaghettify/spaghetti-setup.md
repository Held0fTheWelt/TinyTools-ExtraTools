# Spaghetti setup — editable trigger policy (numeric)

*Path:* `despaghettify/spaghetti-setup.md` — Hub overview: [README.md](README.md).

**Purpose:** **Single editable source** for the **numeric** parts of the despaghettify **trigger policy**: per-category **bars** (operational **%-share ceilings**, strict `**>`**), **M7** category **weights**, and the derived **composite reference** `**M7_ref`**. **How** to run scans, maintain *Open hotspots*, DS rows, Mermaid, and gates stays in `[spaghetti-check-task.md](spaghetti-check-task.md)`; this file is **only** the knobs you retune as structure policy evolves.

**Canonical contract (non-negotiable):**

1. **`spaghetti-setup.md`** — **only** human-edited policy input (bars, weights, `M7_ref`, and any future knobs you add here). Not bidirectional with JSON.
2. **`spaghetti-setup.json`** — **derived artifact** only: regenerate with `python -m despaghettify.tools setup-sync`. **Do not** treat it as a second source of truth or maintain it by hand.
3. **`setup-audit`** — asks: *Does on-disk JSON still match the projection from this Markdown?* If not, the JSON is **stale or wrong** (or Markdown is internally inconsistent), not “two equal truths disagree.”
4. **Parser** — tolerates normal Markdown table styling (e.g. bar cell `12` or `**12**`); semantic structure is the contract, not cosmetic bold.

**Language:** [Repository language](../docs/dev/contributing.md#repository-language).

**Authority:** Values in **this file** are what **“the system”** means for:

- `[spaghetti-check-task.md](spaghetti-check-task.md)` — **Threshold** / trigger evaluation (by reference).
- `[despaghettification_implementation_input.md](despaghettification_implementation_input.md)` — § *Score M7* **formula weights** and § *Trigger policy for check task updates* (must stay aligned after edits here).
- `[templates/despaghettification_implementation_input.EMPTY.md](templates/despaghettification_implementation_input.EMPTY.md)` — same mirror for resets.
- `[templates/despaghettification_completed_log.EMPTY.md](templates/despaghettification_completed_log.EMPTY.md)` — bootstrap for the completed archive (not wiped on reset).

**Important:** **Bars and `M7_ref` apply to real measured shares** (`**Anteil %`** / `metrics_bundle.score.*.anteil_pct` / `condition_shares_pct`), **not** to the **heuristic trigger v2** scale (`category_scores` / `m7` from `ast_heuristic_v2`). Triggers are **advisory** (trend / saturation); see § *Heuristic trigger scale (advisory modes)* below.

## Merge-time monitoring

**Structural metrics are monitored at merge time by the `fy-despaghettify-gate` GitHub Actions workflow.** The gate is **advisory** (non-blocking) and flags:
- New functions over 200 lines
- Nesting depth increases (new functions with nesting >= 6)
- Import cycle increases

Merge is allowed with justification. See `'fy'-suites/fy_governance_enforcement.yaml` for enforcement thresholds and `'fy'-suites/despaghettify/baseline_metrics.json` for baseline snapshot.

**Where which “trigger” numbers live (single confusion point):**


| What you want to edit                                                                              | Canonical location                                                                                                                              |
| -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Per-category bars**, **weights**, `**M7_ref`** (gates on **Anteil %**)                           | **This file** only — then `**setup-sync**` → `[spaghetti-setup.json](spaghetti-setup.json)` (machine projection, not co-equal truth)           |
| **Curve / saturation** for **Trigger v2** (`category_scores` / `m7`, 0–100, **no** bar table here) | Code: `[despaghettify/tools/metrics_bundle.py](tools/metrics_bundle.py)` — `ast_heuristic_category_scores` / `_exp_pressure`; change with tests |


So: **policy thresholds** = **this** `spaghetti-setup.md`; **heuristic metric shape** = `**metrics_bundle.py`**. Both are “trigger-related” but only the first is edited in this Markdown file.

---

## Normative specification (machine contract)

This section is **normative** for tooling in `despaghettify/tools/spaghetti_setup_audit.py` and the **`setup-sync`** / **`setup-audit`** CLIs. Prose elsewhere in this file does not override these rules.

### 1. Purpose and authority

This Markdown file is the **only** human-edited canonical source for **numeric** trigger policy: **`trigger_bars` C1..C7**, **`weights` C1..C7**, and **`m7_ref`**.

**Out of scope here:** heuristic curve implementation, AST scan logic, changing operational definitions of metrics, ROOTS/scope of measurement, and procedural task text (those live in code + task docs).

### 2. Truth model

| Role | Artifact |
|------|----------|
| **Source of truth** | `spaghetti-setup.md` |
| **Derived artifact** | `spaghetti-setup.json` |
| **Consumers** | `metrics_bundle.py`, `check --with-metrics`, audit/diagnostics |
| **Validation** | Always interpret policy from **Markdown first**; JSON must be a lossless projection |

`spaghetti-setup.json` is **never** a co-equal second truth; it is only a machine-readable projection.

### 3. Direction

Only **Markdown → JSON**. Manual edits to JSON are forbidden. **Sync** always regenerates JSON from MD. **Audit** always asks: *Is on-disk JSON still a correct derivation of the current MD?* On mismatch, **fix MD if it is internally wrong; otherwise JSON is stale** — not “two authorities disagree.”

### 4. Semantic configuration

- **`trigger_bars`:** C1..C7 → number; compared to real **`anteil_pct`**; per-category fire iff **strict `>`**.
- **`weights`:** C1..C7 → number; define the weighted composite **`M7_anteil`**.
- **`m7_ref`:** number; composite fire iff **`M7_anteil ≥ m7_ref`**; must satisfy **`m7_ref = Σ weight_i × bar_i`** (tolerance in code).

**Invalid MD:** missing C row, non-numeric cell, **`m7_ref`** inconsistent with bars×weights, **duplicate** row for the same Cn, unknown category (e.g. C8).

### 5. Parser contract

Cosmetic Markdown must not break parsing: e.g. **`12`** vs `12`, **`C3`** vs `` `C3` ``, extra whitespace, blank lines, ragged table alignment — all tolerated for **semantic** table rows under the stable headings **Per-category trigger bars**, **M7 category weights**, **Composite reference**.

**Hard failures:** missing mandatory category, non-numeric value, duplicate Cn, ambiguous row, broken structure.

**Parser output** is a **normalized** dict (no Markdown formatting residue): `trigger_bars`, `weights`, `m7_ref`.

### 6. Sync contract (`setup-sync`)

Load MD → parse → validate **`m7_ref`** vs Σ(weight×bar) → if invalid, **abort with clear error and write nothing** → else emit JSON with **stable key order** and **deterministic** `json.dumps` formatting.

### 7. Audit contract (`setup-audit`)

Separate outcomes (also exposed as **`audit_status`** / **`audit_exit_code`** in machine JSON):

| Code | Status | Meaning |
|------|--------|---------|
| **0** | `PASS` | MD parses; MD internally consistent; JSON matches MD projection |
| **1** | `FAIL_JSON_STALE` | MD OK; derived JSON wrong, missing, or unreadable |
| **2** | `FAIL_MD_INCONSISTENT` | MD parses but **`m7_ref`** ≠ Σ(weight×bar) (and optional JSON drift) |
| **3** | `FAIL_MD_INVALID` | MD unreadable or unparseable |

### 8. UX

Errors must be **actionable** (which section, which row pattern, what was expected). No silent “best effort” if policy is broken.

### 9. Markdown structure

Stable **§ headings** (semantic anchors): **Per-category trigger bars**, **M7 category weights**, **Composite reference**. Free prose, examples, and formatting are allowed **around** those tables; do not fork numeric policy into other files.

### 10. Downstream

- **`metrics_bundle.py`** may read JSON **only** under the assumption it was produced from this MD (`setup-sync`).
- **Task docs** may **reference** this file; they must **not** redefine bars/weights/`m7_ref`.
- **`despaghettification_implementation_input.md`** may mirror formulas in prose but is **not** an authority for digits.

### 11. Tests

Required coverage lives in **`despaghettify/tools/tests/test_spaghetti_setup_audit.py`** (parser edges, consistency, sync determinism, audit outcomes). Extend tests when the parser contract grows.

### 12. One-line project rule

**`spaghetti-setup.md` is the sole human-editable canonical trigger-policy input; `spaghetti-setup.json` is a derived machine mirror only; all audit and sync behavior is directional Markdown → JSON; Markdown formatting differences must not invalidate a semantically correct configuration.**

---

## Architecture — three layers (policy, measurement, advisory)


| Layer                                   | Role                                                                                                                                    | Source of truth                                                                                                                                                                                                                                                                      | Consumed by                                                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| **A — Policy (gates)**                  | **Bars** (%-ceilings), **weights**, `**M7_ref`**. Defines *when* the full spaghetti-check update path runs (DS table, phases, Mermaid). | **This file** (canon); `[spaghetti-setup.json](spaghetti-setup.json)` = **derived** copy for CLIs (`setup-sync`)                                                                                                                                                                      | `metrics_bundle.build_metrics_bundle` (`per_category_trigger_fires`, `composite_trigger_fires`, `trigger_policy_basis` = `anteil_pct`) |
| **B — Measurement (operational %)**     | Seven **Anteil %** values: reproducible counts from AST + import graph (see § *Conditions — operational definitions*).                  | Code: `[despaghettify/tools/spaghetti_ast_scan.py](tools/spaghetti_ast_scan.py)` (`collect_ast_stats`), `[despaghettify/tools/import_cycle_share.py](tools/import_cycle_share.py)` (C1), `[despaghettify/tools/metrics_bundle.py](tools/metrics_bundle.py)` (`condition_shares_pct`) | `check --with-metrics`, `setup-audit`, input list **Anteil %** column                                                                  |
| **C — Advisory heuristic (Trigger v2)** | Saturating 0–100 **scores** for narrative / dashboards; **not** compared to bars in this file.                                          | Code: `ast_heuristic_category_scores` in `[metrics_bundle.py](tools/metrics_bundle.py)`                                                                                                                                                                                              | `metrics_bundle.category_scores`, `score.trigger_v2`; human interpretation only                                                        |


**Evaluation rules (machine, implemented):**

1. **Per-category:** for each **n ∈ {1…7}**, fire if `**Anteil(Cn) > bar_n`** (strict **>**; floats from JSON vs bundle).
2. **Composite:** fire if `**M7_anteil ≥ M7_ref`** with `**M7_anteil = Σ w_i × Anteil(Ci)*`* (same **weights** as in this file).
3. `**trigger_policy_fires`** = per-category **or** composite.

**Boundary:** Changing **what** is measured (numerators, denominators, ROOTS) is a **code + task-doc** change, not a tweak in this file. Changing **how strict** policy is = edit **bars / weights** here (then JSON + `setup-audit`).

---

## Conditions — operational definitions (**Anteil %** used for gates)

These are the **only** values compared to **§ Per-category trigger bars**. All are **percent points** (0–100 scale); rounding in JSON may show decimals.


| Symbol | User-facing name                      | **Anteil %** =                                                                                                 | Numerator                                     | Denominator       | Notes                                                                        |
| ------ | ------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ----------------- | ---------------------------------------------------------------------------- |
| **C1** | Circular dependencies (import cycles) | % of Python **files** under `backend/app` that lie in a **non-trivial SCC** of the **app.*** import graph (v1) | files in cycles                               | files in graph    | **Not** the same as heuristic **C1** in v2 (see § *Internal heuristic v2*).  |
| **C2** | Nesting depth                         | % of measured **functions** with AST nesting depth **≥ 4**                                                     | count `nest_depth ≥ 4`                        | `total_functions` | Depth from `spaghetti_ast_scan` rules.                                       |
| **C3** | Long functions                        | % of functions with **> 100** AST lines                                                                        | `count_over_100_lines`                        | `total_functions` | Line count = AST span of callable body.                                      |
| **C4** | Broad / long callables                | % of functions with **> 50** AST lines                                                                         | `count_over_50_lines`                         | `total_functions` | Overlap with C3 by construction; both can fire independently.                |
| **C5** | Magic numbers (proxy)                 | % of functions with **≥ 5** “non-trivial” **int** literals in body (heuristic; not full global-state analysis) | `count_functions_magic_int_literals_ge_5`     | `total_functions` | Small ints (e.g. 0,1,2,-1) excluded by scanner heuristic.                    |
| **C6** | Duplication / names (proxy)           | % of functions whose **name** appears in **> 1** file                                                          | `count_functions_duplicate_name_across_files` | `total_functions` | Weak proxy for “missing abstraction”; high in repos with many small helpers. |
| **C7** | Control flow / readability (proxy)    | % of functions with nesting **≥ 3** **or** **> 80** AST lines                                                  | `count_functions_control_flow_heavy`          | `total_functions` | Intentionally coarse.                                                        |


**Measurement scope (ROOTS):** fixed list in `[spaghetti-check-task.md](spaghetti-check-task.md)` (Python AST under `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool`). Ignores `.venv`, `__pycache__`, etc.

---

## Internal heuristic v2 — review and change policy

**Purpose:** Produce **bounded** 0–100 scores that rise with “pressure” but **saturate below 100** so a normal repo never prints a misleading literal **100%** on proxy metrics. Used for the **Trigger v2** column and trend talk — **not** for bar comparison.

**How it is built (constants in code — change only with tests):**


| Component          | Rule of thumb (see `ast_heuristic_category_scores`)                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **C2, C3**         | `_exp_pressure` on counts / scale (nesting ≥6 bucket, long100 scale).                                                     |
| **C4**             | `_exp_pressure(18 × L50_ratio)`.                                                                                          |
| **C6**             | `_exp_pressure(40 × L100_ratio)` (tail emphasis, decoupled from C4’s formula).                                            |
| **C1 (heuristic)** | `min(cap, 5 + long100/250×8)` — **legacy proxy**, not the real **C1** cycle %; ignore for cycle truth; use **Anteil C1**. |
| **C5**             | `0.55 ×` heuristic **C4**.                                                                                                |
| **C7**             | `0.65 × max(heuristic C2, heuristic C3)`.                                                                                 |


**Assessment (no code change in this documentation pass):**

- **Keep** the heuristic as-is for now: it is **orthogonal** to gates once policy uses **Anteil %** only; tuning curves without A/B data risks churn.
- **C1 heuristic** is misleading if read as “cycles” — **mitigated** by displaying **Anteil C1** beside it and gating only on **Anteil C1**.
- **C5** does not measure “global state”; the **name** in the bar table is legacy — the gate is explicitly the **magic-int proxy** above.
- **C6** will be high in some codebases; the **bar** is a policy choice, not a bug in the proxy.

**When to change v2 constants:** only after you collect **before/after** `check --with-metrics` bundles and agree the **Trigger v2** column should carry different sensitivity; always update **tests** in `despaghettify/tools/tests/test_metrics_bundle.py`.

---

## Resolved ambiguities (historical)


| Past ambiguity                                             | Resolution                                                                                                     |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Same number shown as “%” for both heuristic and real share | **Two columns** in the input list: **Trigger v2** (0–100, no bar) vs **Anteil %** (measured %, bars apply).    |
| Bars compared to wrong scale                               | **Bars + `M7_ref`** apply **only** to **Anteil %** / `M7_anteil`.                                              |
| Where to edit policy digits                                | `**spaghetti-setup.md`** only; `**setup-sync**` → JSON; validate with `**setup-audit**` (derived vs canon).     |
| What `M7` in JSON means                                    | `**metrics_bundle.m7**` = heuristic weighted sum; `**metric_a.m7**` = `**M7_anteil**` (gated vs `**M7_ref**`). |


---

## Configuration matrix — user vs system


| Item                                                | **User-configurable** (this Markdown only)            | **System-fixed** (code / scan contract)     |
| --------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------- |
| Per-category **bars**                               | Yes                                                   | —                                           |
| **Weights**                                         | Yes (must sum to 1.0)                                 | —                                           |
| `**M7_ref`**                                        | Yes (must equal Σ w×bar)                              | Formula fixed                               |
| **Per-category / composite comparison operators**   | No (implemented: **>** per category, **≥** composite) | In `metrics_bundle.py`                      |
| **Definitions of Anteil (numerators/denominators)** | No                                                    | `spaghetti_ast_scan` + `import_cycle_share` |
| **ROOTS / ignore rules**                            | No                                                    | `spaghetti-check-task` + scanner            |
| **Heuristic v2 curve parameters**                   | No (change in code + tests)                           | `metrics_bundle.py`                         |


---

## Per-category trigger bars (operational %-share ceilings)

Each **bar** is a **maximum acceptable share in percent**, in the **same unit** as `**metrics_bundle.score.categories.Cn.anteil_pct`** (and the **Anteil %** column in the implementation input list). The policy fires the **full** input-list update path when any **live share** is **strictly greater than** its bar (`>`).


| Category                           | Symbol | Bar (fire if **Anteil(C*n*) >** this value, **%**) |
| ---------------------------------- | ------ | -------------------------------------------------- |
| Circular dependencies              | **C1** | **2**                                              |
| Nesting depth                      | **C2** | **8**                                              |
| Long functions + complexity        | **C3** | 12                                                 |
| Multi-responsibility modules       | **C4** | **5**                                              |
| Magic numbers + global state       | **C5** | **0**                                              |
| Missing abstractions / duplication | **C6** | **0**                                              |
| Confusing control flow             | **C7** | **3**                                              |


**Project intent (strict gates):** This repository **intentionally** keeps several bars tight — especially **C5** at **0** (any positive share of the magic-literal proxy triggers) and **C6** at **0** — because **magic-number-style literals** and **cross-file name duplication** are treated as **material risk** to a long-lived framework (structure and reviewability beat ad-hoc literals). A comparatively low composite **`M7_ref`** supports the same posture: the hub prefers **visible**, **repeatable** full check-path maintenance over silently accepting slow structural drift. That is **policy**, not a parser bug.

**Calibration:** The **numeric** cells above may have been chosen under older semantics. After switching to **%-share** gates, you may **re-tune** bars using recent `**check --with-metrics`** output (look at **Anteil %** per category) so thresholds match **current** team intent — **strict** bars may remain unchanged **on purpose**; only adjust when definitions or product goals change, not to “quiet” the hub by default.

---

## M7 category weights

Used in `**M7_ref`** and in the **live composite** `**M7_anteil`** (same formula). **Weights must sum to 1.0.**  
**Preset WOS-STRICT-2 (B):** same per-category **bars** as before; **higher** weight on **C1** (cycles) and **C5** (magic-literal proxy), slightly lower on **C2** / **C4** / **C7** so the composite reflects that priority.


| Symbol | Weight |
| ------ | ------ |
| **C1** | 0.25   |
| **C2** | 0.08   |
| **C3** | 0.18   |
| **C4** | 0.14   |
| **C5** | 0.15   |
| **C6** | 0.12   |
| **C7** | 0.08   |


**Formula (operational %-shares):**  
`M7_anteil = w1×Anteil(C1) + … + w7×Anteil(C7)`  
with **Anteil(C*n*)** from the scan bundle (**%**), **not** the heuristic **trigger v2** scores.

**Terminology (avoid mixing two different numbers):**

- **Live `M7_anteil`** — the weighted sum of **current** **Anteil %** values (`**metric_a.m7`** / `**score.m7_anteil_pct_gewichtet`**). It **changes every run** and is **not** stored in this file.
- `**M7_ref`** — the **single fixed reference** when **each** **Anteil(C*n*)** equals its **bar** from § *Per-category trigger bars* (not live scan values). It **only** changes when you **retune bars or weights** here, then recompute.
- **Heuristic `m7` / `category_scores` (trigger v2)** — **not** compared to these bars; see § *Heuristic trigger scale* for how to use them.

---

## Composite reference (**M7_ref**)

**Definition:** `**M7_ref`** is `**M7_anteil`** when **each** of **Anteil(C1)…Anteil(C7)** is set to **exactly** its **bar** from § *Per-category trigger bars* (not live scan values).

Substituting the **current** bars and weights:

`M7_ref = 0.25×2 + 0.08×8 + 0.18×12 + 0.14×5 + 0.15×0 + 0.12×0 + 0.08×3`

**Update the next two lines whenever you change bars or weights:**


| Field                                                    | Value                                                          |
| -------------------------------------------------------- | -------------------------------------------------------------- |
| **M7_ref** (same unit as **Anteil %** / `**M7_anteil`**) | **4.24**                                                       |
| **M7_ref** (display)                                     | **≈ 4.24** (optional **%** suffix in Markdown for readability) |


**Composite trigger:** run the **full** input-list update path when `**M7_anteil ≥ M7_ref`** (even if no single per-category bar was exceeded yet).

**Scan-only pass:** update **only** § *Latest structure scan* when **no** per-category fire on **Anteil** **and** `**M7_anteil < M7_ref`** (strictly below the numeric **M7_ref**).

---

## Heuristic trigger scale (advisory modes)

The `**ast_heuristic_v2`** values `**category_scores`** / `**m7**` (0–100, saturating curves) are **useful signals** but **not** gated by this file’s bars. Pick a **mode** for how the team uses them (can evolve without changing `metrics_bundle`):

1. **Informative (default)** — show **Trigger v2** beside **Anteil %** in the scan tables; interpret hotspots and prioritisation qualitatively; **all** formal gates use **Anteil** + `**M7_ref`** only.
2. **Dual thresholds (heavy maintenance)** — maintain a **second** numeric table (trigger-scale bars) in addition to %-share bars; wire a separate policy in tooling if you ever need both. Not implemented in the hub CLI today.
3. **Calibrated mapping** — workshop: map **Anteil** ranges to expected **trigger v2** bands so reviewers learn when saturation flattens; still no automatic gate on triggers unless you adopt (2).
4. **Composite-first** — team discussion only: emphasise `**M7_anteil` vs `M7_ref`** and treat per-category bars as secondary; would be a **policy** change (edit this file + checklist), not a code default.

**Recommendation:** Stay on **(1)** until product evidence says otherwise; re-tune **%-share bars** from real `**Anteil`** distributions.

---

## Consistency checklist (after you edit this file)

1. Recompute **M7_ref** from § *Per-category trigger bars* and § *M7 category weights*; update § *Composite reference* (**both** the expansion line and the summary table).
2. Align `[despaghettification_implementation_input.md](despaghettification_implementation_input.md)`: § *Score M7* **Formula** (weights), § *Trigger policy for check task updates* (threshold prose and **M7_ref**), and any narrative that cites old semantics.
3. Align `[templates/despaghettification_implementation_input.EMPTY.md](templates/despaghettification_implementation_input.EMPTY.md)` the same way.
4. Skim `[spaghetti-check-task.md](spaghetti-check-task.md)` **Threshold** — it must **not** reintroduce a second set of numbers; only `[spaghetti-setup.md](spaghetti-setup.md)` is canonical for digits.
5. Run `**python -m despaghettify.tools setup-sync**` to regenerate the derived `[spaghetti-setup.json](spaghetti-setup.json)` (required after bar/weight/`M7_ref` edits; fails if `M7_ref` ≠ Σ w×bar in **this** file).
6. Run `**python -m despaghettify.tools setup-audit`** (optional `**--check-json path/to/check.json`**) — confirms on-disk JSON still matches the **projection** from **this** Markdown; with a check bundle, prints **Anteil %** vs bars from MD; exit **1** if derived JSON is **stale** vs MD.

