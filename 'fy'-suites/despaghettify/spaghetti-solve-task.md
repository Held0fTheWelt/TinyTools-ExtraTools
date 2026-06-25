# Task: Implement despaghettification (wave by wave)

*Path:* `despaghettify/spaghetti-solve-task.md` — Overview: [README.md](README.md).

**Language:** [Repository language](../docs/dev/contributing.md#repository-language). **This task’s scope:** English for all material produced or edited on this track — updates to [despaghettification_implementation_input.md](despaghettification_implementation_input.md), workstream/state Markdown under `despaghettify/state/`, pre/post **artefact** narratives, and **new** code comments or docstrings introduced **for** the invoked **DS-ID** wave.

**Counterpart** to [spaghetti-check-task.md](spaghetti-check-task.md): there, metrics are collected and **Latest structure scan** (including **M7**) is maintained — **without** changing code. The check maintains the **DS table** and **proposed** implementation order when trigger policy is met (per-category score thresholds **or** composite **`M7 ≥ M7_ref`** — numeric policy in [`spaghetti-setup.md`](spaghetti-setup.md)); otherwise the scan section alone is enough for that pass. **Here**, the implementation agent works **one DS-ID at a time**, splits it into **sub-waves**, and runs each sub-wave through the **known governance cycle** (pre → change → post → evidence → state) until that **DS-ID** is **fully closed** in the input list. Between sub-waves there is **no extra human confirmation step** *within the same chat session* while context and gates allow: the agent proceeds **wave k → k+1** autonomously until **all N** complete or a **hard stop** applies (failed gate, missing artefact, contradiction, scope violation, user stop, or voluntary session end — see **Autonomous loop** and **Resume after interruption**).

**Single source of truth (this file):** Invocation, preflight, wave plan, sub-waves, pre/post artefacts, completion gate, **Open hotspots** edits on the solve track, and closure rules are defined **only here**. Cursor skills must **not** duplicate those procedures — they route to this document only.

## Invocation (required)

**This task must be invoked with exactly one open `DS-*` id** from § *Information input list* in [despaghettification_implementation_input.md](despaghettification_implementation_input.md).

- **Canonical form (user / requester):** `run spaghetti-solve-task DS-016` — literal text **`DS-`** plus digits, matching the table (leading zeros **not** required if the table uses none).
- **If no `DS-*` argument is given:** **stop**; reply only with the required invocation pattern and a pointer to § *Information input list* for open IDs.
- **If the ID is missing, malformed, or the row is already CLOSED / struck through:** **stop** with a short explanation.
- **Scope lock for this run:** implementation and artefacts apply **only** to the invoked **DS-ID** (do **not** implement other open DS rows in the same run unless the user explicitly expands scope in a new message).

## Binding sources

| Document | Role |
|----------|------|
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | Canonical: the invoked **DS-* row** (pattern, location, hint, direction, collision), § *Recommended implementation order* (phase, **note** gates, dependencies), § *DS-ID → primary workstream*, § *Latest structure scan* **Open hotspots**; after each sub-wave and at DS closure follow § *Maintaining this file during structural waves*. |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md) | **Completion gate**, pre/post artefacts, state from evidence — **mandatory for every sub-wave**. |
| [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md) | Slugs and mapping to `artifacts/workstreams/<slug>/pre|post/`. |
| Matching `state/WORKSTREAM_*_STATE.md` | Read before the first sub-wave; update after **each** sub-wave and at DS closure from post evidence. |
| [spaghetti-check-task.md](spaghetti-check-task.md) | Optionally re-run after **large** DS closure or at the end to align the **structure scan** with the repo; DS / phase sections only when the check prescribes them via M7 trigger policy (otherwise scan is enough). |

## Do not

- Do **not** touch `docs/archive/documentation-consolidation-2026/*` (see check task).
- Do **not** make closure or success claims without satisfying the **completion gate** from `EXECUTION_GOVERNANCE.md` **for every sub-wave** and again at **DS-level** finalization.
- Do **not** work the same **DS-ID** in parallel with another owner (coordination in the input list).
- No “silent” shortcut: missing pre/post or missing pre→post comparison = **stop**, not keep writing.
- Do **not** skip the **wave plan** (next section): no pre artefacts for wave 1 until the plan exists in-repo or in the same agent turn as explicit numbered steps the user can audit.

## Preflight — scope, dependencies, order

1. **Load the DS row** for the invoked ID (all columns). Load § *DS-ID → primary workstream* → slug → `artifacts/workstreams/<slug>/pre|post/`.
2. **Machine preflight (recommended):** `python -m despaghettify.tools solve-preflight --ds DS-0xx` from repo root. When the DS is **open**, stdout JSON includes **`wave_sizing`**: `effort_score`, `path_signals`, `gate_keywords`, **`n_suggested_min` / `n_suggested_max`**, and **`split_ds_recommended`** if the row is “heavy”. Use that to ground **N** in **Wave sizing** — it is **not** a substitute for an honest decomposition from the **direction** column.
3. **Read § *Recommended implementation order***: find phase row(s) listing this **DS-ID**; read **note** (gates: `pytest`, `ds005`, …) and **dependencies**. If the table says a **hard** prerequisite on another **DS-ID** that is **not** closed in the input list, **stop** and record the blocker (state doc or phase **note**); do **not** partially implement in violation of that dependency.
4. **Consistency:** phase row(s) reference this ID; **collision hint** and repo layout are plausible. Contradiction → [contradiction stop rule](state/EXECUTION_GOVERNANCE.md); do not improvise a second plan file — adjust the input list in-repo only after clarification if the team agrees.
5. **Revision of order (rare):** if order must change, update the **same** input list (phase table, **note**); then continue from an updated wave plan if needed.

## Wave plan — split the DS into sub-waves (mandatory)

Before **any** pre artefacts for this **DS-ID**, the agent **must** define **N ≥ 1** **sub-waves** (numbered **1 … N**), each a **complete** [completion gate](state/EXECUTION_GOVERNANCE.md) unit:

| Sub-wave | Goal (one sentence) | Primary files / symbols | Gate (from DS **hint** / phase **note**: tests, `ds005`, …) |
|----------|---------------------|---------------------------|-------------------------------------------------------------|
| 1 | … | … | … |
| 2 | … | … | … |

Rules:

- Derive steps from the DS row **direction** / **hint** and phase **note**; prefer **smallest** slices that still leave behaviour unchanged and CI green.
- **Naming artefacts:** under the same workstream slug, use **one session date** and the **same DS-ID** in every filename; add a **sub-wave disambiguator** in the stem so pre/post files do not overwrite each other, e.g. `session_YYYYMMDD_DS-016_w01_…`, `…_w02_…` (or `wave01` / `slice_a` — must be **unique** per sub-wave).
- If the DS is explicitly **one-wave-only** in team agreement, **N = 1** is valid; still write the single-row plan.

### Wave sizing — turn “problem length” into **X** simple-sized sub-waves

Goal: each sub-wave is **one reviewable unit** (roughly **one** focused PR / one agent turn), not an unbounded mega-diff.

1. **Size the problem (quick):** from the DS row, list **primary symbols / modules** and the **gates** (pytest paths, `ds005`, …). Cross-check **`solve-preflight` → `wave_sizing`** (`effort_score`, `n_suggested_min` / `n_suggested_max`). Your manual rough **effort score** (distinct files you expect to touch + gate bundles) still applies for choosing **N**; use the CLI block only to **anchor** the same ballpark, not as a formal metric.
2. **One simple task per sub-wave:** after the sub-wave, a reviewer can understand the change as **one** coherent move — e.g. extract **one** helper module, thin **one** entrypoint, or fix **one** import seam — **not** unrelated multi-package churn in the same gate cycle.
3. **Heuristic bounds:** prefer **N ≤ 6** per **DS-ID**. If a honest decomposition needs **> 8** sub-waves, **stop** before coding: split work into **two DS rows** (or a follow-up DS) with team agreement — do not drive **N > 8** under a single ID.
4. **Each table row** must name **concrete** gate commands (copy-pastable) so the sub-wave always ends in **green gate** or **hard stop** — no vague “run tests”.

### Persist the wave plan (required when **N > 1**)

Before **pre** artefacts for sub-wave **1**, copy the **full** wave-plan table (same markdown as above) into the matching **`WORKSTREAM_*_STATE.md`** under a heading such as `## In flight — DS-0xx wave plan (session …)`, **or** into a human-readable file under `despaghettify/state/artifacts/workstreams/<slug>/pre/` whose name includes the **DS-ID** and `wave_plan` (so it is versioned with the branch). This is the **resume anchor** if the chat session ends early.

### Machine-readable mirror (`wave_plan.json`)

Write **`session_YYYYMMDD_DS-0xx_wave_plan.json`** next to the markdown plan (same `pre/` directory and session prefix). It must list the **same** **N** sub-waves, goals, optional `primary_paths`, and **non-empty** `gate_commands` per row. Schema and field rules: [`superpowers/references/WAVE_PLAN_SCHEMA.md`](superpowers/references/WAVE_PLAN_SCHEMA.md).

**Validate before first pre:** `python -m despaghettify.tools wave-plan-validate --file despaghettify/state/artifacts/workstreams/<slug>/pre/<that-json>` (repo-relative path). Exit **2** = fix JSON before coding. Example valid minimal file (fixture, not a real DS): `despaghettify/tools/fixtures/despag_wave_plan_example_valid.json`.

**Optional strict checks:** `--check-primary-paths` (every `primary_paths[]` file exists) and `--gate-prefix-allowlist python,pytest,…` (each gate command must start with one prefix). Use when you want CI-level tightening without changing the base schema.

**Generate / sync Markdown ↔ JSON:** [`despaghettify/tools/wave_plan_emit.py`](tools/wave_plan_emit.py) — `json2md` (emit fenced JSON + table from `wave_plan.json`), `md2json` (extract the first JSON code fence in the Markdown), or `md2json --from-wave-table` after `json2md --table-only` for a round-trip. Reduces drift between the prose table and the machine file.

**Resume hints in JSON (optional):** set **`completed_wave_ids`** (subset of `sub_waves[].id`) and **`next_index`** (`k+1` to continue, or `N+1` when finished) so tooling can pick up the next sub-wave without parsing § *Active progress* alone — see [WAVE_PLAN_SCHEMA.md](superpowers/references/WAVE_PLAN_SCHEMA.md).

## Autonomous loop (until DS finalization)

**Autonomous within one session** means: after each sub-wave passes the completion gate, **immediately** start the **next** sub-wave (read state → pre → implement → post → update list/hotspots) **without** asking the user whether to continue, until **all N** are done **or** a **hard stop** fires — **only while** context, time, and user patience allow. If the session must end with **k < N** completed, **stop** after sub-wave **k**’s gate and follow **Resume after interruption** below (do **not** silently drop remaining waves).

**Hard stop (do not continue to next sub-wave):** failed gate (tests / CI / `ds005` where required), missing artefact, contradiction stop, scope violation, or user interrupt **including** voluntary session end before **N**.

**Human vs agent:** human contributors may still land **one sub-wave per PR** for review comfort; an **autonomous agent** runs as many sub-waves as fit **one** session — then resumes in a **new** invocation using the same **DS-ID** and the persisted plan.

### Resume after interruption (timeout, context limit, user stop, PR merge between waves)

Assume sub-waves **1 … k** completed (**completion gate** satisfied for each), **k < N**, DS **not** finalised.

1. **Truth:** do **not** mark the DS **CLOSED**; repo must reflect **partial** progress only.
2. **Active progress (required):** add or update a row in [despaghettification_implementation_input.md](despaghettification_implementation_input.md) § *Active progress* with **DS-ID**, **`N`**, **`k` completed** (list `_w01`…`_w0k` or artefact stems), **next** sub-wave **`k+1` goal (one line)**, and **relative paths** to the **latest post** artefacts for wave **k**. Do **not** append partial progress to [despaghettification_completed_log.md](despaghettification_completed_log.md).
3. **Next session:** user invokes again **`run spaghetti-solve-task DS-0xx`** (same ID). Agent **reads** persisted wave plan + § *Active progress* + `WORKSTREAM_*_STATE.md`, runs **`python -m despaghettify.tools solve-preflight --ds …`** (optional), then starts **pre** for sub-wave **`k+1` only** — **do not** re-run completed waves unless a gate regressed.
4. If the wave plan is **missing** from the repo and cannot be reconstructed from artefacts + log → **contradiction stop**; restore the table in `WORKSTREAM_*_STATE.md` (or agreed file) before further code.

#### External branch updates (merge / rebase between waves)

If **`main` (or the integration branch) moved** between sub-wave **k** and **k+1** (your PR was merged, you rebased, or you pulled remote changes):

1. **Reconcile** onto the current base (merge or rebase per team convention).
2. **Re-run the completion gate** for the **current tree** before starting **k+1** **pre** (at minimum the **gate_commands** listed for wave **k** in the wave plan, or the phase **note** equivalent). **Do not** re-implement completed earlier waves (**1 … k − 1**) unless post-merge evidence shows **regression** (failing tests, broken imports, or contradiction with persisted pre/post).
3. If **`wave_plan.json`** exists, run **`wave-plan-validate`** again after any manual edit to the plan on the new base.

## Phase 2 — Execute each sub-wave (repeat N times)

For **sub-wave** `k` in `1 … N`:

1. **Read state:** `EXECUTION_GOVERNANCE.md`, `WORKSTREAM_INDEX.md`, matching `WORKSTREAM_*_STATE.md`. If a persisted **`wave_plan.json`** exists for this DS/session, run **`python -m despaghettify.tools wave-plan-validate --file …`** once before **pre** for this `k` (or immediately after editing that JSON); fix validation errors before writing **pre** artefacts.
2. **Pre:** artefacts under `despaghettify/state/artifacts/workstreams/<slug>/pre/` using the **DS-ID** plus a **unique** sub-wave stem fragment (e.g. `_w01_`, `_w02_`, …) for this `k` — at least one human-readable artefact and preferably one machine-readable (`.json`), per governance.
3. **Implementation:** code/structure per the sub-wave row and DS **direction**; preserve behaviour; run the **gate** commands from the wave plan / phase **note**.
4. **Post:** artefacts under `…/post/`; document **pre→post** comparison for this `k`.
5. **State & input list:** update `WORKSTREAM_*_STATE.md` and [despaghettification_implementation_input.md](despaghettification_implementation_input.md) per § *Maintaining this file during structural waves* (§ *Active progress* row per sub-wave when in-flight; completed log only on DS closure — step 2 below).
6. **Open hotspots** (same rules as before, **per sub-wave** when relevant): Still in the **same** PR/commit as this sub-wave, edit **Open hotspots** under § *Latest structure scan* **without** waiting for a new [spaghetti-check-task.md](spaghetti-check-task.md) run. If this sub-wave **fully** fixes a named fragment: **remove** it or set **—** when nothing remains; if **partial**: **rewrite** to remaining risk; if **untouched**: leave unchanged. Do **not** invent new DS rows here — only narrow/close existing hotspot prose.
7. **Next:** if `k < N` and no hard stop → proceed to sub-wave `k+1`. If `k = N` → go to **DS finalization**.

## Phase 3 — DS finalization (once per invoked DS-ID)

After sub-wave **N** completes:

1. **Verify** the DS **direction** / acceptance implied by the row is satisfied (tests and tools listed in the DS row and phase **note** have been run on the final tree unless explicitly deferred with recorded reason — deferral is **discouraged**).
2. **Mark the DS row closed** in § *Information input list* (strikethrough / **CLOSED** on the open row, or remove after the next hub CLI run); update § *Recommended implementation order*; **append one summary row** to [despaghettification_completed_log.md](despaghettification_completed_log.md) (pre/post pointers, session ids for **all** sub-waves); **remove** that wave from § *Active progress*. **Automatic:** any `python -m despaghettify.tools …` invocation runs **`sync-archive`** first — closed rows are moved to the completed log and § *Open* / § *Open phases* are normalized (see [`superpowers/references/CLI.md`](superpowers/references/CLI.md)).
3. **Open hotspots:** final pass per step 6 above for any remaining fragments tied to this DS.
4. **Success message (allowed only now for this invocation):** list **DS-ID**, that **N** sub-waves completed, where pre/post live (paths relative to `despaghettify/state/`), what tests/`ds005` ran on the final state, and optional pointer to a follow-up [spaghetti-check-task.md](spaghetti-check-task.md) run.

Do **not** claim DS success after only a subset of sub-waves unless the wave plan is formally revised to a smaller **N** in the input list with reason.

## Relationship to the check task

| Aspect | [spaghetti-check-task.md](spaghetti-check-task.md) | spaghetti-solve-task.md (this document) |
|--------|---------------------------------------------------|------------------------------------------|
| Change code | No | Yes (structural, per **DS-ID**, sub-wave by sub-wave) |
| Input list | Scan **always**; DS table + order **only propose** when M7 trigger policy is met (see check task) | **Execute** one **DS-ID** per invocation; maintain table/scan/log **during** sub-waves; **Open hotspots** updated when waves resolve them |
| Pre/post artefacts | Only for an explicit wave via another process | **Mandatory per sub-wave** (and documented across **N** slices) |

---

*Goal:* From the **analysis track** (check) to the **execution track** (solve) with a **single DS-ID**, explicit **sub-waves**, and **autonomous** progression through the governance pattern until that DS is **closed** in the canonical input list.
