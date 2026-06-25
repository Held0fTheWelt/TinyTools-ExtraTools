# Spaghetti autonomous agent task (check → solve loop)

*Path:* `despaghettify/spaghetti-autonomous-agent-task.md` — Hub overview: [README.md](README.md).

**Purpose:** If [despaghettification_implementation_input.md](despaghettification_implementation_input.md) still has **open backlog** **DS-*** rows at session start (**Step 0**), **drain them first** with [spaghetti-solve-task.md](spaghetti-solve-task.md) (**one DS-ID per invocation**) **before** the **main cycle** begins — **without** faking closure in the state machine: after **each** slice run **`check --out …`**, then **`autonomous-advance --kind backlog-implement --ds DS-0xx --check-json <repo-relative path>`** while the row stays **open**; **only after** the row is **closed** in the input list, **`autonomous-advance --kind backlog-solve --ds DS-0xx`** (that command **exit 2** while the row is still open). **Main cycle:** run a **full** [spaghetti-check-task.md](spaghetti-check-task.md) pass, then **autonomously** close **open** **DS-*** rows using **solve**, then **check** again; **repeat** until **success conditions** hold **or** a **hard stop** from **in-scope** work fires. Failures that are **clearly outside** the current DS scope or **pre-existing** in the repo **must not** abort this loop by themselves (see **Error scope**).

**Language:** [Repository language](../docs/dev/contributing.md#repository-language).

**Single source of truth (this file):** The **macro loop** (ordering, when to stop, what counts as an abort) is defined **only here**. **Numeric** stop/target rules (**C1..C7**, **`M7_ref`**) are **only** in [spaghetti-setup.md](spaghetti-setup.md). **Check** procedure, **solve** procedure, and governance gates are **only** in their respective task files — do not fork them here.

---

## Invocation (required)

- **Canonical form:** `run spaghetti-autonomous-agent-task` — no **DS-*** argument; the agent picks the **next** open ID from § *Recommended implementation order* then § *Information input list* (see **Pick next DS-ID**).
- **Scope:** One **autonomous session** runs this loop until **success** or **hard stop**. It does **not** replace team review of large diffs; it **chains** existing hub tasks.

---

## Machine guards (hub CLI — **mandatory** for production-style runs)

Use the automation entry point from repo root: `python -m despaghettify.tools …` (see [superpowers/references/CLI.md](superpowers/references/CLI.md)).

1. **Start session:** `python -m despaghettify.tools autonomous-init` before **Step 0**. If a session file already exists, exit **2** — use `autonomous-init --force` only when intentionally resetting. State path: `despaghettify/state/artifacts/autonomous_loop/autonomous_state.json` (typically **gitignored** with the rest of `despaghettify/state/`). JSON schema: [`despaghettify/tools/schemas/autonomous_state.schema.json`](tools/schemas/autonomous_state.schema.json).
2. **After each macro step**, record a **legal** transition (or you cannot prove ordering on resume):
   - **While** a backlog **DS-*** row is **still open** but you finished an **implementation slice** and ran hub **`check --out …`**: `python -m despaghettify.tools autonomous-advance --kind backlog-implement --ds DS-0xx --check-json <relative-path>` — records evidence **without** claiming DS closure; repeat until the row’s goal is met, then close the row in Markdown.
   - **Only after** that **DS-*** row is **closed** in the input list: `python -m despaghettify.tools autonomous-advance --kind backlog-solve --ds DS-0xx` (proves backlog item drained for the state machine).
   - When **no** open backlog **DS-*** remain and you are about to run the **first** full main-cycle check: `python -m despaghettify.tools autonomous-advance --kind main-check --check-json <relative-path>` (path from `check --out …`)
   - After each **main-cycle** **DS-*** closure: `autonomous-advance --kind main-solve --ds DS-0xx`
   - After each **main-cycle** check: `autonomous-advance --kind main-check [--check-json path]`
3. **`autonomous-advance` exit 2** = illegal transition **or** recording **`backlog-solve`** while the **DS-*** row is **still open** → **HARD_STOP** the autonomous task immediately. (**`backlog-implement`** is allowed while the row is open.)
4. **Between waves (recommended):** `python -m despaghettify.tools autonomous-verify` — exit **0** ok, **1** advisory (anti-stall signal from last two check JSONs), **2** hard failure (`HEAD` mismatch vs state, dirty worktree unless `--allow-dirty`, malformed state).
5. **Machine trigger line:** keep [`spaghetti-setup.json`](spaghetti-setup.json) aligned with [`spaghetti-setup.md`](spaghetti-setup.md); run `python -m despaghettify.tools trigger-eval --check-json <path>` after each `check --out`. Optional: `python -m despaghettify.tools check --with-metrics --out …` embeds **`metrics_bundle`** (heuristic **v1**) in the same JSON.

---

## Binding sources

| Document | Role |
|----------|------|
| [spaghetti-setup.md](spaghetti-setup.md) | **When “conditions are met”:** trigger policy **does not** fire (scan-only pass: no per-category **`C*n* > bar_n`** and **`M7 < M7_ref`** per § *Composite reference* / *Scan-only pass*). |
| [spaghetti-check-task.md](spaghetti-check-task.md) | Every **check** phase: full procedure, input list maintenance rules, **Open hotspots**. |
| [spaghetti-solve-task.md](spaghetti-solve-task.md) | Every **implementation** phase: `run spaghetti-solve-task DS-0xx` semantics, wave plan, pre/post, completion gate. |
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | Open **DS-*** rows, § *Recommended implementation order*, scan, workstream map. |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md) | Mandatory completion gate for **each** sub-wave and DS closure — a violation here is an **in-scope hard stop**. |

---

## Open backlog **DS-*** (definition)

For this task, an **open backlog** item is any **DS-*** listed in § *Information input list* in [despaghettification_implementation_input.md](despaghettification_implementation_input.md) that is **not** already **closed** per table conventions there: row **not** ~~struck through~~, **Status** (or equivalent closure column) **not** **Completed** / **CLOSED** / **✓ CLOSED**. The **DS-ID → primary workstream** table may still list an id for history; **authoritative** for “open” is the **information input list** table body.

---

## Success conditions (all must hold after a **post-solve** check)

1. **Structural “conditions met”:** After the latest **check**, the trigger policy in **setup** **does not** fire (same definition as **scan-only** in [spaghetti-setup.md](spaghetti-setup.md)).
2. **No remaining open DS for this track:** There is **no** **DS-*** row in § *Information input list* that is still **open** (not ~~struck~~, not marked **CLOSED** / **Completed** per table conventions in the live input list).

If **(1)** holds but **(2)** does not, **continue** with the next open **DS-*** (the list and plan are authoritative). If **(2)** holds but **(1)** does not, **stop** with a short **advisory**: trigger still fires while no open DS rows remain — use [spaghetti-add-task-to-meet-trigger.md](spaghetti-add-task-to-meet-trigger.md) or a manual planning pass; do **not** invent new **DS-*** rows inside this task unless the user explicitly expands scope.

---

## Macro loop (ordered)

Use a **session log** (bullet list in the reply or a scratch file under `despaghettify/state/` only if your team allows it) listing: **phase** (**backlog** vs **main**), **cycle index**, **check** vs **solve**, **DS-ID** if any, and **outcome** (success / hard stop / advisory stop).

### Step 0 — Backlog drain (**before** the main cycle)

**When:** Run **once** at the **very start** of `run spaghetti-autonomous-agent-task`, **before** **Step 1**.

1. **Detect backlog:** Enumerate all **open backlog** **DS-*** ids (see definition above). Optional: `python -m despaghettify.tools open-ds` from repo root — reconcile with the Markdown table.
2. **If none** → skip Step 0 entirely; go to **Step 1**.
3. **If any** → **do not** run the main-cycle **Step 1** full spaghetti-check until Step 0 is **finished** (backlog empty **or** hard stop). For each backlog id, in **Pick next DS-ID** order (§ *Recommended implementation order* first, then numeric tie-break, same dependency rules as **Step 3**):
   - Run [spaghetti-solve-task.md](spaghetti-solve-task.md) as `run spaghetti-solve-task DS-0xx` — implement in **sub-waves** until the **DS row’s stated goal** is satisfied; **do not** strike / **CLOSE** the row in the input list **before** that goal is met (premature closure is a process failure).
   - After **each** measurable slice: `check --out …` then **`autonomous-advance --kind backlog-implement --ds DS-0xx --check-json …`** (see **Machine guards**).
   - When the goal is met and governance allows closure: **close** the **DS-*** row in the input list, then **`autonomous-advance --kind backlog-solve --ds DS-0xx`**.
   - After each successful DS closure, **re-scan** the input list for remaining open backlog ids.
4. **Between** backlog **implement** slices: **no** full [spaghetti-check-task.md](spaghetti-check-task.md) pass is required unless you need fresh metrics for dependency decisions; **solve-task** gates and governance remain mandatory.
5. When **no** open backlog **DS-*** remain → **Step 1** (main cycle starts here).

**Rationale:** The input list is the **contract** for in-flight work; draining it avoids running a “fresh” check→plan loop while **listed** waves are still incomplete.

### Step 1 — Check (initial, **main** cycle only)

Execute [spaghetti-check-task.md](spaghetti-check-task.md) **in full** (read [spaghetti-setup.md](spaghetti-setup.md) first for numbers). Update [despaghettification_implementation_input.md](despaghettification_implementation_input.md) per that task. **Only after** Step 0 was skipped or completed.

### Step 2 — Evaluate (initial)

- If **Success conditions** (both § above) → **done**; emit **Output format** (below).
- If **hard stop** pending from a **prior** unrelated session → **ignore** for this evaluation unless it blocks gates for the **next** DS (see **Error scope**).
- Else → go to **Step 3**.

### Step 3 — Pick next DS-ID

1. Prefer the **first** phase row in § *Recommended implementation order* that lists an **open** **DS-*** whose prerequisites (phase **note** / dependencies) are satisfied (closed predecessors in the input list).
2. If none: choose the **smallest** numeric **open** **DS-*** in § *Information input list* that still respects **spaghetti-solve-task** dependency rules.
3. Optional: `python -m despaghettify.tools open-ds` from repo root for machine-readable open ids — still reconcile with phase **dependencies**.

If **no** open **DS-*** exists, go to **Step 5** (check only).

### Step 4 — Solve (one DS-ID)

Invoke **exactly** the solve track for that id: follow [spaghetti-solve-task.md](spaghetti-solve-task.md) as for `run spaghetti-solve-task DS-0xx` until that **DS-*** is **CLOSED** in the input list **or** a **hard stop** fires (**failed** completion gate for a sub-wave of **this** DS, missing mandated artefact, contradiction in **this** scope, explicit solve-task stop).

- On **DS closure** → go to **Step 5**.
- On **hard stop** → **abort entire autonomous task**; emit **Output format** with **stop reason** (in-scope).

### Step 5 — Check (post-solve or idle)

Run [spaghetti-check-task.md](spaghetti-check-task.md) **in full** again.

### Step 6 — Evaluate (loop)

- If **Success conditions** → **done**; emit **Output format**.
- If **hard stop** occurred in **Step 4** → already aborted.
- Else if **Anti-stall** (below) → **stop** with diagnostic.
- Else → **Step 3**.

---

## Error scope (what aborts this task vs what is ignored)

**Abort** the autonomous run (**hard stop**) when:

- [spaghetti-solve-task.md](spaghetti-solve-task.md) mandates a stop for the **current** **DS-*** (failed gate **after** the change for a gate declared in the **wave plan** / DS row / phase **note**, missing pre/post, contradiction, scope violation for that DS).
- [spaghetti-check-task.md](spaghetti-check-task.md) cannot be completed due to a **tooling or environment failure introduced or required** during **this** session (e.g. scan script missing, repo unreadable) — not for pre-existing lint noise.

**Do not abort** the autonomous run **only** because of:

- Test failures, warnings, or diagnostics in areas **outside** the **primary_paths** / modules named in the **current** DS **hint** and sub-wave plan, when the **declared** gates for that sub-wave **pass**.
- Known **pre-existing** CI redness documented in the input list or team notes **before** this session, unless the **current** DS’s **mandatory** gates include that suite and it **fails after** your change (then treat as **in-scope** per solve task).

When something fails but is **out of scope**, **record** it in the session summary and **continue** if the solve/check track still allows proceeding.

---

## Anti-stall

If **two** consecutive iterations complete **Step 5** with:

- the **same** set of open **DS-*** ids **and**
- **no** material change in § *Latest structure scan* **M7** / **C1..C7** (same integer scores) **and** the trigger policy **still** fires,

then **stop** with **Output format** marked **advisory stop — no progress** (prevents infinite loops; requires human or add-task).

---

## Optional CLI (helpers only)

- `python -m despaghettify.tools check` — JSON metrics; does **not** replace the markdown check task.
- `python -m despaghettify.tools open-ds` — lists open **DS-*** ids from the input list.
- `python -m despaghettify.tools solve-preflight --ds DS-0xx` — before each solve.

See [superpowers/references/CLI.md](superpowers/references/CLI.md).

---

## Output format (mandatory end state)

Short Markdown:

1. **Outcome:** `SUCCESS` | `HARD_STOP` | `ADVISORY_STOP`.
2. **Backlog (Step 0):** counts of **`backlog-implement`** and **`backlog-solve`** advances, **solve-task** runs, and **DS-*** ids closed before the first main-cycle **check**; `none` if Step 0 was skipped.
3. **Main cycle:** count of **check** runs and **solve** runs after Step 0 (DS-ids listed in order).
4. **Final scan:** one line — trigger fired? yes/no; **M7** and any **C*** still above bar (per **setup**).
5. **Open DS:** none, or list remaining ids.
6. If **HARD_STOP** or **ADVISORY_STOP:** **Reason** in plain language (in-scope error, no progress, trigger fires with no DS rows, …).

---

## Do not

- Do **not** run **clean** or **reset** inside this loop unless the user explicitly asks (destructive to workstreams / input list).
- Do **not** duplicate **bars**, **weights**, or **`M7_ref`** outside **setup**.
- Do **not** implement multiple **DS-*** ids **inside one** solve-task invocation (solve task forbids it unless user expands scope).
