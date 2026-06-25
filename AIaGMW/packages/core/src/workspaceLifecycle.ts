import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type { WorkspaceManifest } from "@aiagmw/shared";
import { relativePath, safeJoin } from "./workspacePaths";
import type { LoadWorkspaceOptions } from "./workspace";
import { loadWorkspace } from "./workspace";

export interface CreateWorkspaceInput {
  root: string;
  id: string;
  name: string;
  description?: string;
}

export async function createWorkspace(input: CreateWorkspaceInput): Promise<{ root: string; manifest: WorkspaceManifest }> {
  const root = path.resolve(input.root);
  const dirs = ["models", "diagrams", "layouts", "proposals/pending", "proposals/accepted", "proposals/rejected", "history"];
  for (const dir of dirs) {
    await mkdir(safeJoin(root, dir), { recursive: true });
  }

  const manifest: WorkspaceManifest = {
    schema: "umlworkspace.v1",
    id: input.id,
    name: input.name,
    description: input.description,
    paths: {
      models: "models",
      diagrams: "diagrams",
      layouts: "layouts",
      proposals: "proposals",
      history: "history",
      imports: "imports",
      exports: "exports",
      docs: "docs"
    },
    features: {
      agentApi: true,
      patchReview: true,
      plantUmlImport: true,
      mermaidImport: true,
      diagramExport: true
    },
    metadata: {
      createdAt: new Date().toISOString()
    }
  };

  const manifestFile = safeJoin(root, ".umlworkspace", "workspace.json");
  await mkdir(path.dirname(manifestFile), { recursive: true });
  await writeFile(manifestFile, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

  return { root, manifest };
}

export function resolveWorkspacePath(workspaceRoot: string, requestedPath: string): string {
  const normalized = requestedPath.trim();
  if (!normalized) {
    throw new Error("Workspace path is required.");
  }
  return safeJoin(path.resolve(workspaceRoot), normalized);
}

export async function openWorkspace(options: LoadWorkspaceOptions) {
  const state = await loadWorkspace(options);
  return {
    root: state.root,
    manifest: state.manifest,
    index: state.index,
    diagnostics: state.diagnostics
  };
}

export function workspaceRelativePath(workspaceRoot: string, absolutePath: string): string {
  return relativePath(path.resolve(workspaceRoot), absolutePath);
}
