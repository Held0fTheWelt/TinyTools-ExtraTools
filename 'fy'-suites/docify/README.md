# Docify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is a **documentation governance** hub: repeatable audits, drift triage, slice-based execution, and evidence-backed backlog rows — not a one-off script drop.

## What Docify is responsible for

- Python **code-adjacent** documentation hygiene (AST audit; optional Google layout hints).
- **Heuristic** documentation drift triage after edits (`git diff` path classification — explicit disclaimer in JSON).
- **Operating discipline** — canonical backlog file, check/solve/reset task tracks, JSON reports.
- **Inline explain assist** — targeted PEP 8 `#` comments / optional synthesizer drafts for a chosen range.
- **Dense contextual explanation** — richer block-by-block inline explanations for functions that are correct but too implicit for readers.

## What Docify is not responsible for

- Semantic proof that prose “matches” behaviour (heuristics only; humans/agents review).
- Product copy, marketing pages, or non-Python ecosystems (unless a task explicitly expands scope).
- Replacing code review, CI, or Despaghettify structural governance.

## Layout

| Path | Role |
|------|------|
| [`tools/`](tools/) | Docify Python package (`docify.tools`) — hub CLI, audit, drift, inline explain |
| [`documentation_implementation_input.md`](documentation_implementation_input.md) | Canonical **DOC-*** backlog + evidence links |
| [`documentation-docstring-synthesize-task.md`](documentation-docstring-synthesize-task.md) | Inline `#` assist → review → `--apply` |
| [`DOCUMENTATION_QUALITY_STANDARD.md`](DOCUMENTATION_QUALITY_STANDARD.md) | House documentation standard for Docify work |

## Hub CLI (preferred)

| Command | Role |
|---------|------|
| `docify audit …` | Same flags as [`tools/python_documentation_audit.py`](tools/python_documentation_audit.py) |
| `docify drift …` | Path-only drift hints from `git diff` (or `--paths-file`) → JSON/text |
| `docify inline-explain …` | Dense contextual inline explanation for a chosen Python function |
| `docify open-doc` | Print open **DOC-*** IDs from the hub backlog |

Examples:

```bash
docify audit --json --out "'fy'-suites/docify/reports/doc_audit.json" --exit-zero
docify drift --json --out "'fy'-suites/docify/reports/doc_drift.json"
docify inline-explain --file fy_platform/ai/base_adapter.py --function prepare_context_pack --mode dense
```

## Quality goal for inline explanations

The goal is **not** to sprinkle vague comments everywhere.
The goal is to explain blocks of intent and responsibility with enough surrounding context that a human reader can follow the code without guessing why each step exists.
