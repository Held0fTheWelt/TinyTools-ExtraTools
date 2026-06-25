# Spaghetti reset task (clean slate + one check pass)

**Purpose:** Run **[`spaghetti-clean-task.md`](spaghetti-clean-task.md)** first (wipe **all** [`state/artifacts/workstreams/`](state/artifacts/workstreams/) session trees and recreate empty `pre|post` per slug; **Step 1b** clears [`state/artifacts/autonomous_loop/`](state/artifacts/autonomous_loop/) and optional `spaghetti_check_last.json`), remove **ephemeral / local** artefacts from the working tree (caches and scratch as below), reset [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) to the **canonical empty template**, then run **[`spaghetti-check-task.md`](spaghetti-check-task.md)** **once** to repopulate § *Latest structure scan* (and, if the trigger policy is met, the DS table and recommended order).

**Order (this task only):** **Reset first, check second.** Steps **1–2** only clean and restore placeholders — they do **not** run the AST scan or fill **C1..C7** / **M7**. Step **3** is the **first and only** analysis pass after the reset: run [`spaghetti-check-task.md`](spaghetti-check-task.md) once; that pass updates the input list from the EMPTY baseline.

**Language:** [Repository language](../docs/dev/contributing.md#repository-language).

---

## Preconditions

- Prefer **repository root** as cwd for the shell steps below (paths are relative to it). The hub CLI (`python -m despaghettify.tools …`) and `despaghettify/tools/spaghetti_ast_scan.py` resolve repo layout from their locations where applicable.
- **Workstream wipe is intentional:** this reset **starts** with [`spaghetti-clean-task.md`](spaghetti-clean-task.md) **Step 1**, which **deletes all files** under `despaghettify/state/artifacts/workstreams/**` and recreates empty `pre/` / `post/` folders. Do **not** run a full reset if you must keep local-only session artefacts with no backup.
- **Autonomous loop state** (`despaghettify/state/artifacts/autonomous_loop/`, including `autonomous_state.json`) is removed by clean **Step 1b** — same irreversibility warning as workstream session files.
- **`artifacts/repo_governance_rollout/`** and any other `artifacts/` trees **not** named in [`spaghetti-clean-task.md`](spaghetti-clean-task.md) remain untouched unless team policy extends the clean.
- If you use `git clean`, **never** use `-x` or `-fd` without reviewing what would be removed; this task uses **explicit paths** only.

---

## Step 0 — Spaghetti clean (workstreams + optional same-pass ephemeral cleanup)

Execute **[`spaghetti-clean-task.md`](spaghetti-clean-task.md)** in full at minimum **Step 1** (workstreams) **and Step 1b** (`autonomous_loop/` + optional `spaghetti_check_last.json`). **Recommended:** also run **Step 2** of that document here so one pass covers workstreams, autonomous state, **and** the ephemeral dirs below (then **skip** duplicating 1a–1c in Step 1 of this document if you already ran clean Step 2).

If you **only** run clean **Step 1** (workstreams) and omit clean **Step 2**, continue with **Step 1** below for caches and hub scratch.

---

## Step 1 — Remove ephemeral directories and despaghettification-adjacent temp

**Skip** this step if you already completed **Step 2** of [`spaghetti-clean-task.md`](spaghetti-clean-task.md) in **Step 0**.

### 1a — Repo-wide caches and build scratch

Delete the following **if they exist** (ignored or regenerable; commonly filled while running checks, pytest, or MkDocs during despaghettification work):

| Path (relative to repo root) | Notes |
|--------------------------------|--------|
| `.state_tmp/` | MkDocs / tooling scratch (see `.gitignore`). Often holds **HTML mirrors** of docs paths (including under `despaghettify/…`) — safe to delete; not governance evidence. |
| `.pytest_cache/` | Pytest cache. |
| `htmlcov/` | Coverage HTML output. |
| `temp_tests_backup/` | Local backup folder if present. |
| `_tmp_goc_dbg/` | Debug scratch if present. |
| `site/` | MkDocs `site/` output **only if** you treat it as disposable build output. |
| `.wos/` | Local operational scratch (see `.gitignore`) if present. |

### 1b — Stores often touched during despag waves / improvement loops

These are **not** under `despaghettify/state/artifacts/**` but are typical **local JSON / run** outputs while exercising backend or engine paths referenced from the input list and solve task:

| Path (relative to repo root) | Notes |
|--------------------------------|--------|
| `backend/var/improvement/` | Improvement-loop operational store (local / test). |
| `backend/var/writers_room/` | Writers Room local store (test / dev). |
| `world-engine/app/var/runs/` | Engine run artefacts (see `.gitignore`). |

### 1c — Ephemeral files inside `despaghettify/` (hub only, not governance)

Remove **loose** scratch files under `despaghettify/` that agents or editors sometimes leave next to the hub docs — **never** delete the canonical task docs, `templates/`, or arbitrary files under `despaghettify/state/` **except** the controlled workstream wipe already done in **Step 0** (which only replaces `state/artifacts/workstreams/`). The scripts below **exclude** `despaghettify/state/` paths from the hub file sweep.

**Eligible patterns** (files only; skip directories `state/`, `templates/`):

- `*.tmp`, `*.bak`, `*.log`, `*~`, `*.swp`, `.DS_Store` (when under `despaghettify/`).

**PowerShell (repo root) — dirs 1a–1b + file sweep 1c:**

```powershell
$dirs = @(
  '.state_tmp', '.pytest_cache', 'htmlcov', 'temp_tests_backup', '_tmp_goc_dbg', 'site', '.wos',
  'backend/var/improvement', 'backend/var/writers_room', 'world-engine/app/var/runs'
)
foreach ($d in $dirs) { if (Test-Path $d) { Remove-Item -Recurse -Force $d } }

$hub = 'despaghettify'
$ext = @('*.tmp', '*.bak', '*.log', '*~', '*.swp')
foreach ($pattern in $ext) {
  Get-ChildItem -Path $hub -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue |
    Where-Object {
      $p = $_.FullName
      $p -notmatch '[\\/]despaghettify[\\/]state[\\/]' -and
      $p -notmatch '[\\/]despaghettify[\\/]templates[\\/]'
    } | Remove-Item -Force
}
if (Test-Path (Join-Path $hub '.DS_Store')) { Remove-Item -Force (Join-Path $hub '.DS_Store') }
Get-ChildItem -Path $hub -Recurse -File -Filter '.DS_Store' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '[\\/]despaghettify[\\/]state[\\/]' } | Remove-Item -Force
```

**Bash (repo root):**

```bash
for d in .state_tmp .pytest_cache htmlcov temp_tests_backup _tmp_goc_dbg site .wos \
         backend/var/improvement backend/var/writers_room world-engine/app/var/runs; do
  [ -e "$d" ] && rm -rf "$d"
done

# 1c: scratch files under despaghettify/ excluding state/ and templates/
find despaghettify -type f \( -name '*.tmp' -o -name '*.bak' -o -name '*.log' -o -name '*~' -o -name '*.swp' -o -name '.DS_Store' \) \
  ! -path 'despaghettify/state/*' ! -path 'despaghettify/templates/*' -delete 2>/dev/null || true
```

**Do not** add `despaghettify/state/` **Markdown state docs**, `.git/`, or user-owned secrets (e.g. `.env`) to deletion lists. Workstream **session files** under `artifacts/workstreams/` are removed **only** via **Step 0** ([`spaghetti-clean-task.md`](spaghetti-clean-task.md)), not by the optional duplicate of 1a–1c here.

---

## Step 2 — Reset the implementation input file

**Canonical empty body:** [`templates/despaghettification_implementation_input.EMPTY.md`](templates/despaghettification_implementation_input.EMPTY.md)

Copy it over the live input (overwrites in place):

**PowerShell:**

```powershell
Copy-Item -Force despaghettify\templates\despaghettification_implementation_input.EMPTY.md despaghettify\despaghettification_implementation_input.md
```

**Bash:**

```bash
cp -f despaghettify/templates/despaghettification_implementation_input.EMPTY.md despaghettify/despaghettification_implementation_input.md
```

After copy, the input list contains **placeholders** (`—`) for **M7**, **C1–C7** (**`%`** on the next check), **AST telemetry** (main scan row + row **under C7** in § *Score M7*), tables, and open hotspots — ready for the next check pass.

**Do not reset** [`despaghettification_completed_log.md`](despaghettification_completed_log.md): it is the long-term archive of **CLOSED** waves and finished check/reset passes. Reset only clears § *Active progress* in the input file (via the EMPTY template). To bootstrap a **new** archive file (e.g. fresh hub), copy [`templates/despaghettification_completed_log.EMPTY.md`](templates/despaghettification_completed_log.EMPTY.md) — or let hub CLI create it from that template on the first `sync-archive` / any subcommand.

---

## Step 3 — Run [`spaghetti-check-task.md`](spaghetti-check-task.md) exactly once

Execute the full procedure from that document **in order**, at minimum:

1. `python "./'fy'-suites/despaghettify/tools/spaghetti_ast_scan.py"` from repo root; capture **N**, **L₅₀**, **L₁₀₀**, **D₆**, and category-relevant context for your **C1–C7** assessment.
2. **Duplicate builtins** grep and **runtime** spot checks as described in `spaghetti-check-task.md` § *Extra checks*.
3. `python "./'fy'-suites/despaghettify/tools/ds005_runtime_import_check.py"` as described there.
4. Update [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) per **Maintaining the input list** in `spaghetti-check-task.md`:
   - **Always:** § *Latest structure scan* (as-of **date and time**; **M7** / **C1..C7** with **`%`**; **AST telemetry** in the main table **and** under **C7** in the § *Score M7* table per [`spaghetti-check-task.md`](spaghetti-check-task.md) §1; extra checks; **Open hotspots** pruned to **unresolved** only).
   - **Only if trigger met** (per-category thresholds **or** composite **`M7 ≥ M7_ref`** — see [`spaghetti-setup.md`](spaghetti-setup.md)): § *Information input list* and § *Recommended implementation order*.
   - **If trigger not met:** do **not** change the DS table or phase table beyond what the reset already set to placeholders.

**Recommended implementation order (explicit obligation after reset):** The EMPTY template clears the phase table to `—`. Step 3 **must** repopulate § *Recommended implementation order* whenever § *Information input list* gets non-placeholder **DS-*** rows. Do **not** stop after the DS table — follow [`spaghetti-check-task.md`](spaghetti-check-task.md) § *Maintaining the input list* → **“How to build a *suitable* phase table”**: cover every DS-ID with a phase, order by runtime/import risk before large orchestrators, assign **primary workstream** per [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md), add **note** gates (`pytest`, `ds005`), include **parallel** bands where independence holds (see check task §3), and add the **mandatory Mermaid `flowchart`** directly under the phase table (§3: **single-line** `["phase · DS-ID · hook"]` labels; fork/join for parallelism). The reset task does **not** fix a global phase order in advance; the **check pass** derives it from the scan + DS rows so [spaghetti-solve-task.md](spaghetti-solve-task.md) has an unambiguous sequence.

**Output to requester:** follow the short **Output format** paragraph at the end of `spaghetti-check-task.md`.

---

## Completion checklist

- [ ] **Step 0** completed: [`spaghetti-clean-task.md`](spaghetti-clean-task.md) **Step 1** (all `artifacts/workstreams/` session content removed; empty `pre|post` per slug recreated) **and Step 1b** (`artifacts/autonomous_loop/` empty; `spaghetti_check_last.json` removed if present).
- [ ] Step **1a–1c** (or clean task **Step 2**) completed: repo caches, wave-adjacent `var/` trees (where present), hub scratch files under `despaghettify/` (excluding `state/` and `templates/`).
- [ ] `despaghettification_implementation_input.md` matches the **EMPTY** template before the check (byte-for-byte optional: diff against `templates/…EMPTY.md`).
- [ ] One full **spaghetti-check** pass completed; scan section filled (**C1..C7** / **M7** as **%**; **AST telemetry** in main table **and** row under **C7** in § *Score M7* per `spaghetti-check-task.md` §1); DS/phases updated only per trigger policy (numeric bars / **`M7_ref`** in [`spaghetti-setup.md`](spaghetti-setup.md)); if DS rows were filled, **§ *Recommended implementation order*** is a **complete** phase table (no `—` placeholders) **and** includes the **mandatory Mermaid** block per `spaghetti-check-task.md` §3.

---

## Maintenance

If governance text in the **EMPTY** template drifts from [`spaghetti-check-task.md`](spaghetti-check-task.md) or [`spaghetti-setup.md`](spaghetti-setup.md) (e.g. new columns, trigger wording, or numeric policy), update **`templates/despaghettification_implementation_input.EMPTY.md`** first, then re-export or copy to the live input when running this reset again.
