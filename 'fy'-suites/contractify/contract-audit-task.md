# Contractify — contract audit task (analysis track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Produce **evidence-backed** contract state: **discovery** (A–E heuristics), **anchoring** hints, **projection** edges, **drift** signals (including deterministic Postman/OpenAPI checks), and **actionable units** suitable for backlog rows in [`contract_governance_input.md`](contract_governance_input.md).

This is the **analysis** counterpart to [`contract-solve-task.md`](contract-solve-task.md).

## Preconditions

- Repository root as current working directory.
- Python 3.14.x (see repo [ADR-0064](../../docs/ADR/adr-0064-python-314-unified-interpreter-standard.md)).
- Optional: `pip install -e .` so the `contractify` console script resolves.

## Procedure

1. **Read scope ceilings** — [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) (automation thresholds, projection rule).
2. **Pre-work context (human)** — skim [`state/PREWORK_REPOSITORY_CONTRACT_REALITY.md`](state/PREWORK_REPOSITORY_CONTRACT_REALITY.md) for repository-specific anchors already known.
3. **Run machine audit** — emit a local ephemeral JSON under `reports/` and compare its stats against the tracked markdown snapshot when needed:

   ```bash
   python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/_local_contract_audit.json"
   ```

4. **Interpret drift** — treat `drift_findings` as **evidence**:
   - `deterministic: true` → fix or acknowledge promptly when severity ≥ medium.
   - `deterministic: false` → human triage; do not auto-rewrite normative docs from heuristics.
5. **Interpret conflicts** — read `conflicts[]` alongside drift (implemented in [`contractify.tools.conflicts`](tools/conflicts.py); versioning helpers in [`contractify.tools.versioning`](tools/versioning.py); bounded graph edges in [`contractify.tools.relations`](tools/relations.py)):
   - Use **`classification`** and **`severity`** (see [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) **Conflict classifications**) to pick the remediation pattern.
   - Use **`kind`** plus **`normative_candidates` / `observed_candidates` / `projection_candidates`** when present to route ownership without re-parsing evidence strings.
   - Prefer **`normative_sources`** vs **`observed_or_projection_sources`** when filing **CG-*** rows so ownership is obvious.
   - High-confidence deterministic conflicts may also appear under `actionable_units` as **`[conflict:<severity>|conflict-deterministic]`** — dedupe with `conflicts[]` when scheduling work.
6. **Backlog** — translate `actionable_units` into **one row per coherent slice** in [`contract_governance_input.md`](contract_governance_input.md) (prefer concrete scopes, not counts).
7. **Cursor skill sync** — if `superpowers/*/SKILL.md` changed:

   ```bash
   python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"
   ```

## Outputs (verification artefacts)

- local `reports/_local_contract_audit.json` (or slice-local path).
- tracked `reports/CANONICAL_REPO_ROOT_AUDIT.md` for human review evidence.
- For **reviewable frozen payloads** matching the hermetic tree, see [`reports/committed/`](reports/committed/) (regenerate with `python -m contractify.tools.freeze_committed_reports`).
- Updated **CG-*** rows in `contract_governance_input.md` when work is scheduled.

## Completion (analysis slice)

Done when JSON is reviewed, high-severity deterministic drifts and material **`conflicts[]`** rows are triaged (or explicitly deferred with rationale), and the backlog lists the next **solve** slices with owners or ordering notes.

## References

- Drift methods: [`README.md`](README.md) section **Drift detection (implemented methods)**.
- Conflict table: [`README.md`](README.md) section **Conflict detection (implemented)** and scope doc **Conflict classifications** in [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md).
- Solve track: [`contract-solve-task.md`](contract-solve-task.md)
- Reset: [`contract-reset-task.md`](contract-reset-task.md)
