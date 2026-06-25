# `'fy'-suites` — catalog

This directory groups **cross-cutting “fy” work**: tasks that **support how the monorepo is operated and evolved** (structure, API contracts in clients, agent workflows, hygiene) **without being part of the shipped product surface** (game, player apps, runtime story code). Think **meta-pipelines**: valuable for **project processing**, not the feature layer itself.

Use this file as the **catalog**: scan the table, jump to a suite’s `README.md`, then follow that suite’s CLI and Cursor skills.

---

## Suite catalog

| Suite | What it does | Python package / CLI | Cursor skills (source → sync) |
|-------|----------------|----------------------|--------------------------------|
| [**`fy_platform/`](fy_platform/README.md)** | Shared portability primitives: project root resolution, manifest loading, versioned artifact envelope, bootstrap utilities. | `python -m fy_platform.tools` · `fy-platform` | _N/A (platform core, no router skills)_ |
| [**`despaghettify/`](despaghettify/README.md)** | Structure / “spaghetti” checks, DS-style workflow Markdown, metrics, autonomous loop helpers. | `python -m despaghettify.tools` · `despag-check` / `wos-despag` | [`superpowers/`](despaghettify/superpowers/README.md) → `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"` |
| [**`postmanify/`](postmanify/README.md)** | Refresh Postman collections from OpenAPI; emit **master** + **per-tag sub-suites** under `postman/`. | `python -m postmanify.tools` · `postmanify` | [`postmanify-sync`](postmanify/superpowers/postmanify-sync/SKILL.md) → `python "./'fy'-suites/postmanify/tools/sync_postmanify_skills.py"` |
| [**`docify/`](docify/README.md)** | Python docstring backlog audit (AST), optional Google-layout checks, PEP 8 `#` comment / Google docstring assists for a single file. | `python "./'fy'-suites/docify/tools/python_documentation_audit.py"` · `python "./'fy'-suites/docify/tools/python_docstring_synthesize.py"` | [`superpowers/`](docify/superpowers/README.md) → `python "./'fy'-suites/docify/tools/sync_docify_skills.py"` |
| [**`delagecy/`](delagecy/README.md)** | Governed legacy discovery, register-first reporting, approval tracking, UI residue checks, and removal gates. | `python -m delagecy.tools` · `delagecy` | _N/A (policy + gate suite)_ |
| [**`contractify/`](contractify/README.md)** | Contract discovery, anchoring vs projections, relation edges, drift (incl. OpenAPI ↔ Postman manifest), governance backlog **CG-***. | `python -m contractify.tools` · `contractify` | [`superpowers/`](contractify/superpowers/README.md) → `python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"` |
| [**`templatify/`](templatify/README.md)** | Own and validate reusable templates for docs, reports, context packs, and suite outputs. | `python -m templatify.tools` · `templatify` | _N/A (template governance suite)_ |

---

## Quick start (any suite)

1. **Repo root:** `pip install -e .` (see root [`pyproject.toml`](../pyproject.toml)) so importable packages under `'fy'-suites/` resolve.
2. **CLI:** prefer `python -m <package>.tools …` or the console scripts listed in the table.
3. **Cursor:** edit `superpowers/*/SKILL.md` in the suite, then run the suite’s **`sync_*_skills.py`** so **`.cursor/skills/`** stays the committed mirror.

---

## Conventions (all suites)

| Topic | Rule |
|-------|------|
| **Paths** | Invoke scripts with a repo-relative path, e.g. `python "./'fy'-suites/<suite>/tools/…"`. |
| **Package naming** | Directory name under `'fy'-suites/` matches the **importable** package (`despaghettify`, `postmanify`). Avoid a `tools/<suite>.py` file that shadows the package name. |
| **Skills** | Router-only `SKILL.md` files; **procedure** stays in task Markdown at suite root or in `references/`. |
| **Links** | Markdown under `superpowers/references/` needs **one extra `../`** segment to reach the repo root than when the hub lived at the repository root. |

---

## Adding a new suite (checklist)

1. Create **`'fy'-suites/<suite>/`** with `__init__.py`, `README.md`, and `tools/` (CLI + optional `tests/`).
2. Register the package in **[`pyproject.toml`](../pyproject.toml)** (editable install must discover it; avoid overlapping `include` filters that drop other suites).
3. Add a row to the **Suite catalog** table above and, if applicable, a **Superpower** under `superpowers/` plus a `sync_<suite>_skills.py` script pattern.
4. Point **`AGENTS.md`** and **`CONTRIBUTING.md`** at the new suite so agents and humans share one discovery path.
5. If shared platform behavior is added, update **`fy_platform/compatibility_matrix.wave1_baseline.json`** and related tests.

---

## Naming note

The package root is **`'fy'-suites`**. In prose we refer to suites here as **“fy” suites** — **f**ramework for **y**ard-wide (repo-wide) **meta** work — not application features.


## Next-stage additions

- `contractify consolidate` generates and can safely apply ADR/test reflection scaffolding when mappings are unambiguous.
- `testify` now audits whether consolidated ADRs are explicitly mirrored in tests, not merely behaviorally passing.
- root `requirements.txt`, `requirements-test.txt`, and `requirements-dev.txt` are included.


- `templatify` now governs reusable output templates for docs, reports, context packs, and suite-facing markdown generation.


## New in this build

- `docify` can now generate denser inline explanations for Python functions.
- `securify` is integrated as the security lane of the fy suites.


## End-product additions

- `securify/` is now part of the core suite set.
- `usabilify/` and `templatify/` are first-class suites in the catalog.
- `fy-platform suite-catalog` writes a generated full suite catalog.
- `fy-platform command-reference` writes a generated command reference.
- `fy-platform export-schemas` writes JSON-schema-style contract files.
- `fy-platform doctor` writes a top-level health and next-step report.
- `fy-platform final-release-bundle` writes the final release bundle for the current workspace.

| [**`mvpify/`**](mvpify/README.md) | Imports prepared MVP bundles, mirrors their docs into the governed workspace, and orchestrates next-step implementation across suites. | `python -m mvpify.tools.hub_cli` · `mvpify` | Uses the shared registry/index/journal/router and observes imported MVPs through observifyfy. |
| [**`metrify/`**](metrify/README.md) | Measure AI usage, model spend, output volume, and utility signals across fy-suites; feed summaries back into observifyfy. | `python -m metrify.tools` · `metrify` | _N/A (AI measurement suite)_ |

- `fy-platform ai-capability-report` writes the current suite AI capability matrix and aspirational next upgrades.


## Internal mirror root

Compatibility and mirrored internal product docs now live under `internal/`. Legacy nested documentation layouts are migrated forward and are no longer used as active release paths.
