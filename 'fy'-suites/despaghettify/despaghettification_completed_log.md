# Despaghettification — completed work log (archive)

*Path:* `despaghettify/despaghettification_completed_log.md` — Overview: [README.md](../README.md).

**Purpose:** Long-running record of **finished** despaghettification waves (closed **DS-***, completed check/reset passes, merged PRs). Keeps [despaghettification_implementation_input.md](../despaghettification_implementation_input.md) small — that file holds only **open** DS rows and in-flight progress.

**Language:** [Repository language](../../docs/dev/contributing.md#repository-language) — English for all rows.

**Do not** mirror completed rows back into the input § *Open* tables. Formal evidence remains under `despaghettify/state/artifacts/…` and `WORKSTREAM_*_STATE.md` per [EXECUTION_GOVERNANCE.md](../state/EXECUTION_GOVERNANCE.md).

## When to append here (mandatory)

| Event | Action |
|-------|--------|
| **DS-ID closed** ([spaghetti-solve-task.md](../spaghetti-solve-task.md) finalization) | Append **one** summary row to § *Completed waves* (**newest first**); remove from input § *Open*. |
| **Partial wave** (`k < N`) | Input § *Active progress* only — not here until **CLOSED**. |
| **`spaghetti-check`** / **`spaghetti-reset`** | Append if logged; clear input § *Active progress*. |
| **Bulk archive** | If § *Active progress* has **>5** rows, move oldest closed rows here (keep ≤3 active in input). |
| **Hub CLI `sync-archive`** | Automatic on every `python -m despaghettify.tools …` run (see [CLI.md](../superpowers/references/CLI.md)). |

---

## Closed DS detail

Full row text formerly in the input list — kept here so the input file stays lean. Optional batch subheading: `### Batch YYYY-MM-DD`.

| ID | pattern | location (typical) | outcome (done) | gates / evidence |
|----|---------|--------------------|----------------|------------------|
| — | — | — | — | — |

**Recommended order used:** — *(fill when archiving a multi-DS batch, e.g. phase 1 DS-001 → phase 2 DS-002)*

---

## Completed waves

| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |
|------|-------|-------------------|----------------------------------------|----------------------------------------|----------------------|-------------|
| — | — | — | — | — | — | — |

**New rows:** append at the **top** of this table (newest first). For a multi-DS session, add one row per **DS-ID** plus optional detail rows in § *Closed DS detail* above.
