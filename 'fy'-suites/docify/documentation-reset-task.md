# Docify — documentation backlog reset (recovery track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Restore the canonical **documentation backlog** file from the empty template when the working
document is corrupted, duplicated, or abandoned mid-session. This is intentionally lighter than
Despaghettify's full hub reset: Docify does not maintain a numeric trigger matrix.

## Preconditions

- You have a **git** checkpoint (commit or stash) if the current backlog still contains unique
  coordination notes you might need later.

## Procedure

1. Copy [`templates/documentation_implementation_input.EMPTY.md`](templates/documentation_implementation_input.EMPTY.md)
   over [`documentation_implementation_input.md`](documentation_implementation_input.md).

2. Optionally archive deleted content to `state/artifacts/` as a dated Markdown file when the
   team still needs the narrative.

3. Run **one** fresh [`documentation-check-task.md`](documentation-check-task.md) pass to
   rebuild backlog rows from audit/drift JSON.

## When not to use this

If the backlog is merely **stale**, prefer editing rows in place or adding new **DOC-*** rows
instead of wiping coordination history.
