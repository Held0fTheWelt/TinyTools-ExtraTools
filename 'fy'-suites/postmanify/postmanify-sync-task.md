# Postmanify sync task

*Path:* `'fy'-suites/postmanify/postmanify-sync-task.md` — Hub overview: [README.md](README.md).

**Language:** [Repository language](../../docs/dev/contributing.md#repository-language). **This task’s scope:** English for any new or edited hub Markdown, manifest notes, and PR descriptions for Postmanify work.

## Purpose

Keep **machine-generated** Postman collections aligned with the **canonical OpenAPI** inventory under `docs/api/openapi.yaml`. **Committed** API exercise coverage lives in **`postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json`** and **`postman/suites/`** — extend behaviour by editing **`docs/api/openapi.yaml`** (and Postmanify when you need richer examples or scripts), not by reviving removed hand-only collection JSON files in-repo.

## Outputs (after `generate`)

| Artifact | Location |
|----------|----------|
| Master collection (all tags as folders) | **`postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json`** (default `generate` output; override with `--out-master` if needed) |
| Per-tag sub-suites | `postman/suites/WorldOfShadows_Suite_<TagSlug>.postman_collection.json` |
| Manifest (OpenAPI path + sha256 + file list) | `postman/postmanify-manifest.json` |

## Procedure

1. Confirm `docs/api/openapi.yaml` is current (or pass `--openapi` to another checked-in spec).
2. Run **`python -m postmanify.tools plan`** and skim counts (tag folders, total generated requests).
3. Run **`python -m postmanify.tools generate`** from the repository root (requires **`pip install -e .`** so `import postmanify` resolves). Pass **`--out-master`** only when you intentionally write the master collection somewhere other than the default path above.
4. In Postman (or Newman), import **`postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json`** plus a standard environment (`WorldOfShadows_Local` / `WorldOfShadows_Docker`) and spot-check a few routes per tag.
5. For focused work, import only the relevant **`postman/suites/WorldOfShadows_Suite_*.postman_collection.json`** sub-suite.
6. **Review:** diff `postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json` and relevant **`postman/suites/`** files; adjust **`docs/api/openapi.yaml`** (or Postmanify code) if routes or grouping are wrong — do not resurrect removed hand-only collections in-repo without an explicit maintainer decision.
7. Commit updated **`postman/`** outputs (complete + suites + manifest) and **`postman/README.md`** when you intend others to pick up the new export.

## CLI reference

See [`superpowers/references/CLI.md`](superpowers/references/CLI.md).
