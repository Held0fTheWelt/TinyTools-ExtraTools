# Docify documentation quality standard

**Language:** Maintainer-facing text in this hub follows the repository language policy in
[`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language).

## Scope

This standard governs **how** Docify expects Python comments, docstrings, and suite-local
Markdown to be written when Docify-driven work is in scope. It does **not** replace product
documentation style guides outside the hub unless a task explicitly adopts it.

## Baselines

- **PEP 8** — readability, naming, and comment placement expectations for Python.
- **PEP 257** — docstring *role* (module/class/function docstrings exist where they carry
  contract value; first line is a concise summary when a docstring is present).

## House layering (explicit)

PEP 257 is **not** identical to Google-style sections. When a public function already uses
Google-style `Args:` / `Returns:` blocks, keep them accurate and minimal. Docify's optional
`--google-docstring-audit` flags structural gaps — it is a **layout** check, not proof of good
documentation.

## Writing rules (normative for Docify slices)

1. **Document intent and contracts** — invariants, accepted inputs, errors raised, side
   effects, and integration edges that are not obvious from signatures alone.
2. **Do not narrate the obvious** — avoid comments that restate what the next line of code
   clearly does.
3. **Prefer docstrings at boundaries** — public modules, public classes, and public functions
   deserve the clearest summaries and parameter/return semantics when non-trivial.
4. **Prefer inline `#` comments for local traps** — non-obvious reasoning, performance or
   security caveats, domain constraints, and deliberately unusual control flow.
5. **Keep private helpers light** — internal functions do not need ceremonial prose unless
   complexity warrants it.
6. **Tests are not prose targets** — avoid flooding tests with template docstrings unless the
   repository explicitly standardises that.

## Drift and evidence

Documentation claims must remain **checkable**. When behaviour changes, update the smallest set
of layers that keeps truth aligned (often: local docstrings + one higher-level doc). Docify's
`drift` command emits **heuristic** hints from paths — treat it as triage input, not automatic
truth.

## AST audit nuance (Docify default scanner)

Private ``ast.NodeVisitor`` subclasses (class names starting with ``_``) skip ``visit_*`` method
docstrings in the missing-docstring audit. Those hooks are usually mechanical traversal and
rarely carry public contract value; public visitors should use non-underscored class names if
you want them held to the default bar.

## Suite self-coherence

Docify applies the same rules to its own package: tools should be discoverable, documented at
their CLI boundaries, and covered by tests where behaviour is easy to get wrong (parsing,
classification, report JSON).
