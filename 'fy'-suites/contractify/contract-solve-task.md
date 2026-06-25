# Contractify — contract solve task (implementation track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Execute **one bounded contract-governance slice** with before/after evidence (for example: fix Postman projection drift after OpenAPI change; add explicit projection back-links in a `docs/easy/` page; record a supersession edge in an ADR).

## Preconditions

- A **CG-*** backlog row exists in [`contract_governance_input.md`](contract_governance_input.md) with clear acceptance criteria.
- You have the latest tracked `reports/CANONICAL_REPO_ROOT_AUDIT.md` snapshot or can re-run a local audit export after edits.

## Procedure

1. **Anchor first** — confirm which file is **normative** for the slice (OpenAPI, normative index entry, ADR, workflow YAML). Do not invent a parallel truth document.
2. **Implement** — minimal change set (projection fix, manifest regen, link repair, ADR cross-link).
3. **Verify** — re-run:

   ```bash
   python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/_local_contract_audit.json"
   ```

4. **Evidence** — attach tracked markdown references and, when useful, local JSON diff notes to the CG row; mark status.
5. **Sibling suites** — if the slice is doc-heavy, use **docify** for AST/doc repairs; if API collections, use **postmanify**; if structural tangle, route follow-up to **despaghettify**.

## Completion

The slice is done when audit shows the targeted drift cleared or explicitly accepted with rationale, and the backlog row reflects closure evidence.
