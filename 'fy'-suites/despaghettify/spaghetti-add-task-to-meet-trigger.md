# Task: Add DS tasks to meet a C-category trigger (planning pass)

*Path:* `despaghettify/spaghetti-add-task-to-meet-trigger.md` — Hub overview: [README.md](README.md).

**Language:** [Repository language](../docs/dev/contributing.md#repository-language).

**Purpose:** Given a **single target category** **C1**–**C7** from [spaghetti-setup.md](spaghetti-setup.md) § *Per-category trigger bars* / [input list](despaghettification_implementation_input.md) § *Trigger policy*, **propose or extend** **DS-*** rows in § *Information input list* so implementers have concrete waves that **pull that category’s score below** its threshold once executed. In the **same pass**, **re-sort and re-validate** § *Recommended implementation order* (all active phases): **dependencies**, **parallelism** (e.g. `3a` / `3b`), **collision hints**, and the **mandatory Mermaid** `flowchart` so the plan stays consistent with [spaghetti-check-task.md](spaghetti-check-task.md) §2–§3.

This task is **planning and Markdown only** — it does **not** replace a full [spaghetti-check-task.md](spaghetti-check-task.md) run for fresh **M7** / telemetry / *Open hotspots* numbers. After editing the input list, prefer a follow-up **spaghetti-check** when the repo or scan materially changed.

**Single source of truth (this file):** Required inputs, binding sources, checklists, and **Markdown-only** edit rules for this **add-task** pass are defined **only here**. **Per-category numeric trigger values** (bars, weights, **`M7_ref`**) are authoritative in [spaghetti-setup.md](spaghetti-setup.md) — read that file; do not copy numbers into skills. Cursor skills route here; they must not duplicate this task’s steps.

---

## Binding sources

| Document | Role |
|----------|------|
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | **Edit:** § *Information input list* (DS table), § *Recommended implementation order* (phase table + Mermaid), § *DS-ID → primary workstream* when new IDs appear. **Read:** § *Latest structure scan* for current **C1..C7** **`%`**, **M7**, **Open hotspots**, AST telemetry. |
| [spaghetti-setup.md](spaghetti-setup.md) | **Numeric** policy: per-category **bars**, **M7** weights, **`M7_ref`**, composite vs scan-only. |
| [spaghetti-check-task.md](spaghetti-check-task.md) | §1 scan rules, §2 DS row rules (**pattern** must lead with **C1..C7**), §3 Mermaid and parallelism. |
| [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md) | **Primary workstream** slug for each **DS-*** (`artifacts/workstreams/<slug>/pre|post/`). |
| [despaghettify/tools/spaghetti_ast_scan.py](tools/spaghetti_ast_scan.py) | Evidence for **C3** (length), **C2** (nesting in script output where applicable), leaderboard paths — script resolves repo root from its path. |

---

## Required input (single parameter)

**Target category:** exactly one of **`C1`**, **`C2`**, **`C3`**, **`C4`**, **`C5`**, **`C6`**, **`C7`**.

Record it at the top of your run note (PR / issue / session text): *“`spaghetti-add-task-to-meet-trigger` for **C*n***.”*

If the current scan already shows **C*n* ≤ threshold**, this task is still allowed as **proactive backlog** (optional DS rows for further reduction), but state that explicitly in the **hint / measurement idea** or **note** so implementers do not confuse it with a firing trigger.

---

## Category → structural intent (use when drafting DS rows)

Use this mapping to keep **DS-*** rows honest and tied to the **M7** category definitions in [spaghetti-check-task.md](spaghetti-check-task.md).

| Symbol | Focus when proposing DS waves |
|--------|--------------------------------|
| **C1** | Circular / fragile import seams — extract protocols, DTO modules, narrow `TYPE_CHECKING` islands; align with `ds005` and runtime import checks. |
| **C2** | Deep nesting — flatten control flow, extract phases, reduce `nest_depth` hotspots named in scan / script output. |
| **C3** | Long functions and complexity — split orchestrators, extract phase modules; cite AST line bands and `spaghetti_ast_scan.py` leaders. |
| **C4** | Multi-responsibility modules — separate HTTP vs policy vs persistence seams per file cluster. |
| **C5** | Magic numbers and global state — centralise constants, shrink mutable globals, configuration surfaces. |
| **C6** | Duplication and missing abstractions — consolidate helpers, shared validators, one canonical path. |
| **C7** | Confusing control flow — clarify branching, state machines, naming; reduce cross-cutting `if` ladders where the scan calls it out. |

Each new or updated **pattern** cell must start with the **target** **C*n*** first, then optional secondary symbols if the wave also clearly hits another category — form **`C3 · …`** or **`C3 · C4 · …`**, per [spaghetti-check-task.md](spaghetti-check-task.md) §2.

---

## Procedure

### 1) Read current truth

1. Open [despaghettification_implementation_input.md](despaghettification_implementation_input.md): § *Latest structure scan* (**C1..C7** **`%`**, **M7**, **Open hotspots**, telemetry).
2. Open [spaghetti-setup.md](spaghetti-setup.md): confirm **C*n*** **trigger** (strict `>` vs bar — same numbers as in the input list trigger policy, which mirrors **setup**).
3. If **C3** / **C2** / length-nesting evidence is stale or missing, run `python "./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"` from repo root and use **top longest** / **top nesting** lines as candidates (do not paste the full leaderboard into *Open hotspots*; the check task curates that).

### 2) Propose one or more **DS-*** rows for **C*n***

- **Prefer new DS-* numbers** only for genuinely new topics; **update** an existing open row if it already tracks the same file cluster.
- Each row: **ID**, **pattern** (**`C*n* ·`** …), **location**, **hint / measurement idea**, **direction**, **collision hint** (parallel risk).
- **Series of tasks** is expected when one category (e.g. **C3**) needs several slices across packages — split so each wave has one **primary workstream** and realistic **gates** (`pytest …`, `ds005`).
- **Do not** invent DS rows unrelated to lowering **C*n*** without marking them as a different initiative (out of scope for this pass).

### 3) Maintain § *DS-ID → primary workstream*

Add or update rows for every **new** **DS-*** so pre/post paths stay unambiguous ([WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)).

### 4) **Recommended implementation order** — full pass on all active phases

Treat this as a **re-planning** step over the **entire** phase table (not only new DS):

1. **Enumerate** every open **DS-*** that still appears in § *Information input list* (or merged explicitly in one phase row).
2. **Order** by **risk and blast radius** per [spaghetti-check-task.md](spaghetti-check-task.md) §3 *Heuristic* and the numbered “How to build a suitable phase table” list: runtime/import seams before huge orchestrators unless **C*n***-targeted waves are clearly isolated in another package.
3. **Dependencies:** if phase B needs artefacts from A, state it in **note**; only claim **hard** deps when imports or tests justify it.
4. **Parallelism:** for independent waves (different **primary workstream**, no shared hot files, no hard import coupling), use **parallel bands** (`3a` / `3b`, etc.) and **fork/join** in Mermaid; document **collision** where parallel work still touches adjacent surfaces.
5. **Mermaid:** refresh the **mandatory** `flowchart` under the phase table — **single-line** nodes `["phase · DS-ID · hook"]` per §3; keep labels aligned with the table.
6. Remove or **mark done** phase rows that match **closed** DS rows so the table does not imply work on completed IDs.

### 5) Consistency checks before exit

- [ ] Every open **DS-*** from § *Information input list* is covered by at least one phase row (unless explicitly merged).
- [ ] No phase row lists only **closed** IDs as if still pending.
- [ ] **pattern** on every touched DS row begins with **C1..C7** per §2.
- [ ] **Mermaid** reflects **parallel** vs **sequential** edges consistently with **note** columns.

---

## Do not

- Do **not** change application code inside this task file’s procedure — implementation stays with [spaghetti-solve-task.md](spaghetti-solve-task.md) and [EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md).
- Do **not** silently rewrite § *Latest structure scan* numbers unless you are also executing [spaghetti-check-task.md](spaghetti-check-task.md) with real commands for that timestamp.
- Do **not** leave **resolved** items in **Open hotspots** when you touch the input list for unrelated reasons (check task pruning rule).

---

## Output (short, for the requester)

3–6 sentences: name the **target C*n***; how many **DS-*** rows were added or updated; which **workstreams**; whether **Recommended implementation order** gained parallel bands or a stricter sequence; pointer to changed sections in [despaghettification_implementation_input.md](despaghettification_implementation_input.md).

---

## Relation to other hub tasks

| Situation | Use |
|-----------|-----|
| Full metric refresh, trigger evaluation, optional DS churn from scan | [spaghetti-check-task.md](spaghetti-check-task.md) |
| Targeted **C*n*** backlog + **re-sort all phases** | **This document** |
| Implement waves with pre/post | [spaghetti-solve-task.md](spaghetti-solve-task.md) |
