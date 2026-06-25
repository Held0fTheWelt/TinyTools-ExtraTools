# Postmanify

Hub for **refreshing Postman collections** from the repository **OpenAPI** description and emitting **per-tag sub-suites**.

## Quick start

```bash
pip install -e .   # repo root
python -m postmanify.tools plan
python -m postmanify.tools generate --out-master postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json
```

The **`--out-master`** path controls where the **single full-tree** collection is written; `postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json` is the recommended location for a repo-visible “complete OpenAPI” suite next to the hand-maintained **`WorldOfShadows_Complete`** file.

Optional shared-platform outputs:

- `--envelope-out path/to/postmanify.envelope.json` emits a versioned machine-readable envelope.
- When `fy-manifest.yaml` defines `suites.postmanify.openapi`, `out_master`, or `suites_dir`, those values become defaults.

## Layout

| Path | Role |
|------|------|
| [`postmanify-sync-task.md`](postmanify-sync-task.md) | Agent procedure: plan → generate → review → commit `postman/` outputs. |
| [`superpowers/`](superpowers/README.md) | Cursor router skills; sync into `.cursor/skills/` via `tools/sync_postmanify_skills.py`. |
| [`tools/cli.py`](tools/cli.py) | CLI implementation (`python -m postmanify.tools`). |
| [`tools/openapi_postman.py`](tools/openapi_postman.py) | OpenAPI → Postman v2.1 JSON builders. |

## Relationship to `postman/`

- **Generated (canonical):** `postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json`, `postman/suites/*.postman_collection.json`, `postman/postmanify-manifest.json` — regenerate with **`generate`**; diff against OpenAPI history when reviewing PRs.
- **Legacy hand collections** (`WorldOfShadows_Complete`, `Smoke`, `API`) were **removed**; extend behaviour by improving OpenAPI + Postmanify templates, or by layering local Postman changes that you do not commit.
