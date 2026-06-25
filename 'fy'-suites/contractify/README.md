# Contractify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is **contract governance**: discovery, anchoring, projection edges, drift, and backlog-friendly **actionable units** — not product feature code.

## What Contractify is

- **Discovery** — finds likely contracts using explicit A–E heuristics (see below).
- **Anchoring model** — distinguishes **normative** anchors vs **observed** surfaces vs **verification** artifacts.
- **Projections** — audience/mode views (easy, AI-reading, specialist) that **must** trace back to anchors.
- **Relations** — discovery emits core edges; [`contractify.tools.relations`](tools/relations.py) **`extend_relations()`** adds bounded **`references`**, **`indexes`**, **`implements`**, **`operationalizes`**, explicit ADR **`supersedes`**, workflow→OpenAPI **`validates`**, and index-ambiguity **`conflicts_with`** (plus fy-suite handoff cross-links) when evidence exists.
- **Drift analysis (`driftify`)** — [`contractify.tools.drift_analysis`](tools/drift_analysis.py): deterministic checks first, heuristics labelled honestly.
- **Conflicts** — [`contractify.tools.conflicts`](tools/conflicts.py) **`detect_all_conflicts()`**: duplicate normative index targets, ADR vocabulary buckets, projection↔OpenAPI fingerprint mismatches, orphan **`source_contract_id`**, projections pinning **superseded**/**deprecated** contract ids, Active/Binding index rows vs retired ADRs, and bounded lifecycle/supersession header gaps — each row carries **`classification`**, **`severity`**, **`kind`**, optional candidate buckets, and normative vs projection source lists.
- **Versioning (operational)** — [`contractify.tools.versioning`](tools/versioning.py) parses **`info.version`** from OpenAPI and explicit **`Status:`** lines in ADR headers so `ContractRecord.version` / lifecycle **`status`** reflect declared anchors (not inferred code behaviour).

## What Contractify is not

- Not a documentation generator — use **docify** to repair Python/docs readability.
- Not OpenAPI authoring — use product/API workflows; Contractify **reads** OpenAPI as anchor.
- Not structural refactors — use **despaghettify** after Contractify shows tangled truth.

## Maturity (known boundaries)

Phase-1 tooling is **deliberately shallow** in places: conflicts are real but not semantic (no normative↔implementation contradiction mining, no test-derived conflict classes, no rich supersession graph). Versioning reads **declared** OpenAPI and ADR header signals only — no automatic breaking-change taxonomy or cross-family migration workflows. Use **CG-*** backlog rows and human review for anything that needs semantic judgement. For **ZIP / copy exports**, strip `__pycache__` / `*.pyc` or use `git archive`; see [`examples/README.md`](examples/README.md) and [`reports/README.md`](reports/README.md).

## Core truth model

| Term | Meaning |
|------|---------|
| **Contract** | Declared or structurally inferred obligation across a boundary (API, runtime seam, workflow, policy). |
| **Anchor** | Canonical place a contract lives (OpenAPI file, normative index, ADR, workflow YAML). |
| **Projection** | Derived artefact for a tool/audience (Postman collection, easy doc). **Must** reference its anchor contract. |
| **Normative truth** | What is governed / intended / declared correct. |
| **Observed reality** | What code and runtime currently do — **evidence**, not auto-truth. |
| **Drift** | Evidence that anchor, projection, implementation, or tests diverge meaningfully. |

## Discovery heuristics (A–E)

| Tier | Meaning | Examples in this repo |
|------|---------|------------------------|
| **A** | Explicit markers or known canonical paths | `docs/dev/contracts/normative-contracts-index.md`, `docs/api/openapi.yaml`, `docs/ADR/adr-*.md`, `spaghetti-setup.md`, **`'fy'-suites/postmanify/postmanify-sync-task.md`**, **`'fy'-suites/docify/documentation-check-task.md`** |
| **B** | Structural workflow / CI / ops / shared schemas | `.github/workflows/*.yml`, `docs/operations/OPERATIONAL_GOVERNANCE_RUNTIME.md` (when present), up to **two** `schemas/*.json` files per pass |
| **C** | Referencing / audience artefacts | `docs/easy/**`, `docs/start-here/**` modelled as projections |
| **D** | Out of scope by default | Private helpers — not scanned |
| **E** | Confidence | Stored per record; automation policy in [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) |

Every discovered row includes `discovery_reason` so classification is **inspectable**.

## Drift detection (implemented methods)

| Drift class | Method | Deterministic? |
|-------------|--------|----------------|
| **api_runtime** | Compare `postmanify-manifest.json` `openapi_sha256` to SHA-256 of the referenced OpenAPI file | Yes |
| **anchor_projection** | Audience markdown under `docs/easy` / `docs/start-here` must link to `normative-contracts-index` or contain `contractify-projection:` | Heuristic (text signal) |
| **suite_handoff** | Docify default AST roots include `'fy'-suites/contractify` | Yes (file content check) |
| **suite_handoff** | Postmanify sync task prose **`openapi_path`** vs `postmanify-manifest.json` | Yes (when both files exist) |
| **planning_implementation** | Contract **`implemented_by`** paths missing on disk | Yes (when declared) |
| **missing_propagation** | `spaghetti-setup.md` present without `spaghetti-setup.json` | Yes (presence) |

Heuristic findings use **low** severity by default; deterministic OpenAPI hash mismatch uses **high**.

## Conflict detection (implemented)

| Signal | Deterministic? | `classification` (typical) |
|--------|----------------|-----------------------------|
| Same resolved markdown target linked twice from the normative index | Yes | `normative_anchor_ambiguity` |
| Two+ ADRs hit the same bounded vocabulary bucket | No (keyword bucket) | `normative_vocabulary_overlap` |
| Projection `contract_version_ref` (16-hex OpenAPI prefix) ≠ current file SHA prefix | Yes | `projection_anchor_mismatch` |
| Projection `source_contract_id` not present in the discovery inventory for this pass | Yes (inventory) | `projection_anchor_mismatch` (kind: `projection_to_anchor_mismatch`) |
| Projection pins a **superseded** / **deprecated** discovered contract id | Inventory + lifecycle | `lifecycle_projection_vs_retired_anchor` |
| `Status: Deprecated/Superseded` in ADR head without supersession navigation cues | No | `supersession_gap` |
| Normative index row reads **Active**/**Binding** but links to a **superseded**/**deprecated** ADR | Row heuristic | `superseded_still_referenced_as_current` |

## Integration with sibling fy suites

| Suite | Handoff |
|-------|---------|
| **docify** | Drift pass **`drift_docify_contractify_scan_root`** if contractify is missing from default AST roots; discovery may emit **`CTR-DOCIFY-TASK-001`** when `documentation-check-task.md` exists. Docify repairs prose/code readability — Contractify does not synthesise docstrings. |
| **postmanify** | **`drift_postman_openapi_manifest`** (SHA) plus **`drift_postmanify_task_openapi_path_alignment`** (path prose vs manifest); projections remain derived from **`CTR-API-OPENAPI-001`**. |
| **despaghettify** | **`drift_despag_setup_derived_json`** surfaces missing derived JSON; tangled anchors feed **DS-** backlog — Contractify does not refactor structure. |

## Hub CLI

With **`pip install -e .`** at the repository root ([`pyproject.toml`](../../pyproject.toml)) the **`contractify`** console script is available. Equivalent: **`python -m contractify.tools`**.

| Command | Role |
|---------|------|
| `discover` | Contracts + projections + relations (JSON). |
| `audit` | Full pass + drift + conflicts + `actionable_units`. |
| `self-check` | Same payload as `audit` (integration sanity). |

Examples:

```bash
contractify audit --json --out "'fy'-suites/contractify/reports/_local_contract_audit.json"
python -m contractify.tools discover --out "'fy'-suites/contractify/reports/_local_contract_discovery.json" --quiet
```

Canonical repository run profile:

- Run from repository root with `fy-manifest.yaml` present.
- If `fy-manifest.yaml` defines `suites.contractify.max_contracts`, the default `discover` / `audit` CLI uses that ceiling automatically.
- World of Shadows currently pins the canonical audit profile this way so the runtime/MVP spine is reproducible without hidden `--max-contracts` knowledge.

Optional shared-platform output:

- `--envelope-out path/to/contractify.envelope.json` writes a versioned envelope around discover/audit payloads.
- If `fy-manifest.yaml` defines `suites.contractify.openapi`, contract discovery/drift/conflict checks use that anchor default.

## Layout

| Path | Role |
|------|------|
| [`superpowers/`](superpowers/) | Cursor router `SKILL.md` files |
| [`tools/`](tools/) | Python package (`contractify.tools`) |
| [`contract_governance_input.md`](contract_governance_input.md) | **CG-*** backlog |
| [`contract-audit-task.md`](contract-audit-task.md) | Analysis procedure |
| [`contract-solve-task.md`](contract-solve-task.md) | Bounded implementation procedure |
| [`contract-reset-task.md`](contract-reset-task.md) | Recovery |
| [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) | Ceilings + automation thresholds |
| [`state/ATTACHMENT_PASS_INDEX.md`](state/ATTACHMENT_PASS_INDEX.md) | Visible index for major Contractify state-tracked passes |
| [`state/PREWORK_REPOSITORY_CONTRACT_REALITY.md`](state/PREWORK_REPOSITORY_CONTRACT_REALITY.md) | Human snapshot of pre-suite reality |
| [`state/COMPLETION_PASS_STATE.md`](state/COMPLETION_PASS_STATE.md) | Completion / hardening pass record |
| [`state/FINALIZATION_PASS_2026-04-13.md`](state/FINALIZATION_PASS_2026-04-13.md) | Final bounded completion: baseline, slices, evidence, honest limits |
| [`state/LAST_MILE_CLOSURE_2026-04-13.md`](state/LAST_MILE_CLOSURE_2026-04-13.md) | Last-mile closure: committed report fixtures, projection↔retired signal, evidence alignment |
| [`state/RUNTIME_MVP_SPINE_ATTACHMENT.md`](state/RUNTIME_MVP_SPINE_ATTACHMENT.md) | Current runtime/MVP spine attachment record: promoted anchors, evidence attachments, precedence, unresolved overlaps |
| [`examples/`](examples/) | Committed JSON **shape** samples + [`examples/README.md`](examples/README.md) |
| [`reports/`](reports/) | Ephemeral local JSON at `reports/*.json` (gitignored) + tracked human-readable markdown snapshots + [`reports/README.md`](reports/README.md) + tracked [`reports/committed/`](reports/committed/) hermetic **discover/audit** fixtures |

## Cursor skills

```bash
python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"
python "./'fy'-suites/contractify/tools/sync_contractify_skills.py" --check
```

Do **not** hand-edit only `.cursor/skills/` copies for Contractify — sync overwrites them.

## Tests

```bash
python -m pytest "'fy'-suites/contractify/tools/tests" -q
```

**Hermetic default:** unit tests patch ``repo_root()`` to a **synthetic mini-repo** (see ``tools/tests/conftest.py``) so ``pytest`` passes in **ZIP extracts** and partial trees without the full monorepo ``pyproject.toml`` next to your checkout layout. Pure logic tests (``test_models.py``, sample JSON shape tests) skip the patch.

**Optional CLI override:** set ``CONTRACTIFY_REPO_ROOT`` to an existing directory that contains a hub ``pyproject.toml`` marker for ``world-of-shadows-hub`` so ``python -m contractify.tools …`` resolves the repo without walking from the installed package path.

**Committed samples:** ``examples/contract_discovery.sample.json`` and ``examples/contract_audit.sample.json`` illustrate JSON shape; ``tools/tests/test_example_artifacts.py`` guards compatibility when fields change. **Full hermetic payloads:** ``reports/committed/*.hermetic-fixture.json`` (regenerate via ``python -m contractify.tools.freeze_committed_reports``); ``tools/tests/test_committed_reports.py`` guards substance.

## Extending the suite

1. Add a **deterministic** check when a new machine manifest exists (copy the Postmanify pattern).
2. Add **heuristics** with conservative confidence and clear `discovery_reason` text.
3. Never mark `<0.60` confidence items as `source_of_truth: true`.
4. Prefer new **relations** over duplicating contract rows.

## Versioning

OpenAPI contracts use **`info.version`** when present; ADRs use explicit **`Status:`** lines for lifecycle (`active`, `deprecated`, `superseded`, …) and optional **`Supersedes:`** lines (parsed for **`supersedes`** relation edges when both ADRs are discovered). Other anchors remain **`unversioned`** until the repository adds machine-readable markers. Breaking vs non-breaking change tracking stays **manual** in **CG-*** backlog rows; projection rows may carry **`contract_version_ref`** (e.g. manifest SHA prefix) for drift and conflict checks.

## Current state-tracked governance wave

For state-tracked visibility of the current runtime/MVP governance wave, start with [`reports/CANONICAL_REPO_ROOT_AUDIT.md`](reports/CANONICAL_REPO_ROOT_AUDIT.md), then compare it with [`state/RUNTIME_MVP_SPINE_ATTACHMENT.md`](state/RUNTIME_MVP_SPINE_ATTACHMENT.md), [`reports/runtime_mvp_attachment_report.md`](reports/runtime_mvp_attachment_report.md), [`contract_governance_input.md`](contract_governance_input.md), and a fresh local `reports/_local_contract_audit.json` export if machine detail is needed.
