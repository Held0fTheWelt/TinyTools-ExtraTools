# Docify — documentation solve task (implementation track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Execute **one** coherent documentation slice tied to a **DOC-*** backlog row in
[`documentation_implementation_input.md`](documentation_implementation_input.md), then
re-verify with objective artefacts.

## Preconditions

- A **DOC-*** row exists and is marked **OPEN** using `| **DOC-nnn** |` in the backlog table.
- The slice scope is **bounded** (one package boundary, one feature surface, or one suite
  self-governance pass — not whole-repo prose rewrites).

## Procedure

1. **Confirm scope** — re-read the DOC row, linked code paths, and any drift JSON that motivated
   the slice.

2. **Implement documentation only** — docstrings, targeted `#` comments, and repository
   Markdown updates that align truth. Follow
   [`DOCUMENTATION_QUALITY_STANDARD.md`](DOCUMENTATION_QUALITY_STANDARD.md). Do **not** change
   runtime behaviour unless the slice explicitly includes a behaviour fix (rare; out of band
   for normal Docify slices).

3. **Re-run verification**:

   ```bash
   python -m docify.tools audit --root path/to/slice --json --exit-zero
   ```

   When the slice was opened because of behaviour changes, also re-run drift on the same diff
   window you care about and confirm follow-up layers were addressed.

4. **Close the backlog row** — mark the DOC row closed using `~~DOC-nnn~~` in the table and add
   a short evidence note (paths to JSON, PR link, or command transcript).

5. **Optional style tooling** — when in scope, run Ruff via `python -m docify.tools audit --with-ruff`
   on the same roots.

## Completion gate

The DOC row is **CLOSED** only when: the slice reads truthfully against code, audit is clean
for the agreed symbol scope (or remaining gaps are explicitly deferred with a new DOC row),
and evidence links are recorded.

## References

- Analysis track: [`documentation-check-task.md`](documentation-check-task.md)
- Quality standard: [`DOCUMENTATION_QUALITY_STANDARD.md`](DOCUMENTATION_QUALITY_STANDARD.md)
