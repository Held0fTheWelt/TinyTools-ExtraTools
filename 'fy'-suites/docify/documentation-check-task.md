# Docify — documentation check task (analysis track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Produce **evidence-backed** documentation state: Python docstring gaps (AST), **heuristic**
follow-up hints after code changes (path classification), and a **slice-ready** backlog in
[`documentation_implementation_input.md`](documentation_implementation_input.md).

This is the **analysis** counterpart to [`documentation-solve-task.md`](documentation-solve-task.md).

## Preconditions

- Repository root as current working directory (or pass explicit `--repo-root` flags).
- Python 3.14.x available (repo standard).
- `git` on `PATH` when using drift against a revision range (skip `drift` when using a manual
  `--paths-file`).

## Procedure

1. **House standard** — skim [`DOCUMENTATION_QUALITY_STANDARD.md`](DOCUMENTATION_QUALITY_STANDARD.md)
   so findings are classified with the same vocabulary used in the backlog.

2. **Drift triage (optional but recommended after meaningful edits)** — emit JSON for review
   and attach paths under `reports/` or `state/artifacts/` as your session prefers:

   ```bash
   python -m docify.tools drift --json --out "'fy'-suites/docify/reports/doc_drift.json"
   ```

   Interpretation guide: see **Disclaimer** field in the JSON. This is **path-only** heuristics.

3. **Python AST audit** — default roots include the Docify suite itself for self-governance:

   ```bash
   python -m docify.tools audit --json --out "'fy'-suites/docify/reports/doc_audit.json" --exit-zero
   ```

   Narrow with `--root path/to/slice` when you already know the package under inspection.

4. **Backlog maintenance** — translate JSON + review notes into **one row per coherent slice**
   in [`documentation_implementation_input.md`](documentation_implementation_input.md). Prefer
   actionable scopes (for example: *“backend API v1 governance routes — contract docstrings”*)
   instead of raw counts.

5. **Cursor skill sync** — if router skills under `superpowers/` changed, run
   `python "./'fy'-suites/docify/tools/sync_docify_skills.py"` and commit `.cursor/skills/`
   updates.

## Outputs (verification artefacts)

Minimum for a serious pass:

- `reports/doc_drift.json` (when drift ran) or an equivalent machine-readable export.
- `reports/doc_audit.json` (or slice-local audit JSON).
- Updated **Documentation backlog** table rows in `documentation_implementation_input.md`.

## Completion (analysis slice)

Analysis is **done for the slice** when: drift hints are reviewed (accepted/rejected with
reason), audit JSON reflects the intended scan roots, and the backlog lists the next **solve**
slices with clear owners or ordering notes.

## References

- Drift CLI: `python -m docify.tools drift --help`
- Audit CLI: `python -m docify.tools audit --help` (same flags as the legacy script path).
- Solve track: [`documentation-solve-task.md`](documentation-solve-task.md)
- Python-only deep dive (still valid): [`documentation-audit-task.md`](documentation-audit-task.md)
- Inline explain assist: [`documentation-docstring-synthesize-task.md`](documentation-docstring-synthesize-task.md)
