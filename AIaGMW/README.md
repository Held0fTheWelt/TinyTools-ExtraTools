# AIaGMW

AIaGMW is an **AI-Assisted Graphical Modeling Workspace**: a local-first,
folder-based UML/modeling editor where the semantic model is the source of
truth, diagrams are views, and AI co-authors work through reviewable patches.

**Normative architecture:** [Git/docs/architecture/plugins/AIaGMW/architecture.md](../../Git/docs/architecture/plugins/AIaGMW/architecture.md)  
**UML traceability:** [Git/UML/Plugins/AIaGMW/TRACEABILITY.md](../../Git/UML/Plugins/AIaGMW/TRACEABILITY.md)

## Current implementation

- TypeScript monorepo: `frontend`, `backend`, `packages/shared`, `packages/core`, `packages/connectors`
- Diagram types: class, component, package, sequence, state, activity, deployment (via `DiagramRouter`)
- Patch engine with import-as-patch, diff preview, approval, history
- Agent tools: read, `model_validate`, `context_pack_build`, `proposal_revise`, proposal submit/preview/apply
- Optional AKDB connector (disabled by default)
- PlantUML/Mermaid import/export + SVG/PNG image export
- Architecture validation via `.umlworkspace/rules.json`

## Local development

```bash
pnpm install
pnpm dev
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:3000/api/health

## Useful commands

```bash
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm build
pnpm workspace:sample
pnpm --filter @aiagmw/backend agent:smoke
```

## Optional AKDB connector

Core editing works with **no connectors**. To enable AKDB context and normative diagram import:

```powershell
$env:AIAGMW_CONNECTORS_ENABLED = "akdb"
$env:AIAGMW_AKDB_URL = "http://127.0.0.1:8787"
$env:AIAGMW_AKDB_PROJECT_ID = "tiny-tool-development"
$env:AIAGMW_AKDB_EXPORT_ROOT = "D:\TinyToolDevelopment\Git\UML\Plugins\AIaGMW\staging"
pnpm dev:backend
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `AIAGMW_CONNECTORS_ENABLED` | _(empty)_ | Comma-separated; `akdb` enables connector |
| `AIAGMW_AKDB_URL` | `http://127.0.0.1:8787` | AKDB HTTP base |
| `AIAGMW_AKDB_PROJECT_ID` | `tiny-tool-development` | AKDB project |
| `AIAGMW_AKDB_EXPORT_ROOT` | `{repo}/exports/akdb-staging` | Staged PlantUML for publication |

**Publication workflow:** Export PlantUML from workspace → commit to `Git/UML/Plugins/AIaGMW/` → `akdb_reingest_project`. Git/UML wins on publication conflicts.

Connector API:

- `GET /api/connectors/status`
- `POST /api/connectors/akdb/context`
- `GET /api/connectors/akdb/diagrams`
- `POST /api/connectors/akdb/import`

## Docker

```bash
docker compose up --build
```

The backend reads the mounted workspace from `MODEL_WORKSPACE_ROOT`.

## Workflows

### Manual modeling

1. Open or create a workspace.
2. Select a diagram (palette adapts to diagram type).
3. Add elements, connect relations, edit in inspector.
4. Use auto-layout from the toolbar when needed.
5. Undo/redo from the top bar.

### Import (patch review)

1. Click import in the top bar.
2. Paste PlantUML or Mermaid; preview conflicts.
3. Submit creates a pending proposal.
4. Approve and apply from the proposals panel.

### Export

- PlantUML/Mermaid: export dialog → `exports/` folder
- SVG/PNG: `POST /api/export/diagrams/:id/image` with canvas capture content

### Agent co-author

```bash
pnpm --filter @aiagmw/backend agent:smoke
```

MCP stdio adapter: `tsx backend/src/mcp/stdioServer.ts`

## Workspace model

- `.umlworkspace/workspace.json`, optional `rules.json`
- `models/*.umlmodel.json`, `diagrams/*.diagram.json`, `layouts/*.layout.json`
- `proposals/**/*.patch.json`, `history/*.json`

No database required for canonical model state.
