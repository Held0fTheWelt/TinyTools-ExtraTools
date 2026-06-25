# Docify — Python documentation audit task

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — committed Python **comments** and **docstrings** are **English** only; this task adds **procedure** for using Docify tooling, not a second copy of the policy.

## Purpose

Produce an evidence-backed backlog of missing or empty module/class/function docstrings, then clear it **incrementally** without changing business logic (documentation and formatting only). For the **full governance pass** (drift JSON + backlog rows), start from [`documentation-check-task.md`](documentation-check-task.md) instead of this Python-only shortcut.

## Preconditions

- Repository root as current working directory (or pass `--repo-root` explicitly).
- Python 3.14.x available (repo standard).

## Procedure

1. **Baseline** — run the audit tool. Default roots (no `--root`) include **`'fy'-suites/docify`** so the suite self-audits with the rest of the monorepo slice; narrow with ``--root`` when you need a smaller pass. Excludes `**/migrations/**`, `**/site-packages/**`, `world-engine/source/**`, and test trees unless you pass `--include-tests`:

   ```bash
   python -m docify.tools audit --json --out "'fy'-suites/docify/reports/doc_audit.json" --exit-zero
   ```

   Use `--include-tests` or `--include-private` only when the slice requires it. Inspect `summary` and `findings` in the JSON.

2. **Choose one slice** — one package directory, service module, or a single file path (via `--root …` repeated if needed). Do not attempt whole-repo docstring rewrites in a single changeset.

3. **Optional layout check** — on symbols that already have docstrings, add `--google-docstring-audit` (with optional `--docstring-max-line 72`) to flag missing `Args`/`Returns` sections, missing `Type:`-style line after `Returns:`, or overlong docstring lines.

4. **Implement** — add or improve **English** docstrings (Google or NumPy style, match surrounding code). Adjust PEP 8–level formatting only when needed for the same edit. **Do not** change behavior, public contracts, or tests except where a docstring corrects a wrong description (rare; verify with code).

5. **Re-run audit** on the same slice until the slice is clean:

   ```bash
   python -m docify.tools audit --root path/to/slice --exit-zero
   ```

6. **Optional style pass** — if `ruff` is installed: `python -m docify.tools audit --root path/to/slice --with-ruff --exit-zero` (informational; fix Ruff issues only when in scope for the slice).

7. **Cursor sync** — if you edited [`superpowers/`](superpowers/) router skills, run `python "./'fy'-suites/docify/tools/sync_docify_skills.py"` from repo root and commit `.cursor/skills/` updates (see root [`AGENTS.md`](../../AGENTS.md)).

## Completion

Slice is done when: targeted modules have usable docstrings; tests for touched code still pass; audit on the slice shows no remaining `MISSING_OR_EMPTY_DOCSTRING` for symbols in scope.

## References

- Audit CLI: ``python -m docify.tools audit`` (same flags as ``'fy'-suites/docify/tools/python_documentation_audit.py``; `--help`).
- Docify inline explain (PEP 8 `#` comments for a range, same hub): [`documentation-docstring-synthesize-task.md`](documentation-docstring-synthesize-task.md) and ``'fy'-suites/docify/tools/python_docstring_synthesize.py``.
- Repository language: [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language).
