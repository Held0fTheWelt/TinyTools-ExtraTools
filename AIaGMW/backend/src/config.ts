import path from "node:path";

export interface AppConfig {
  host: string;
  port: number;
  repoRoot: string;
  workspaceRoot: string;
  workspacesParent: string;
  schemaDir: string;
  akdbUrl: string;
  akdbProjectId: string;
  connectorsEnabled: string[];
  akdbExportRoot: string;
}

export function getConfig(): AppConfig {
  const repoRoot = path.resolve(process.env.AIAGMW_ROOT ?? path.join(process.cwd(), ".."));
  const workspaceRoot = path.resolve(process.env.MODEL_WORKSPACE_ROOT ?? path.join(repoRoot, "sample-workspace"));
  const workspacesParent = path.resolve(process.env.AIAGMW_WORKSPACES_PARENT ?? path.join(repoRoot, "workspaces"));
  const schemaDir = path.resolve(process.env.AIAGMW_SCHEMA_DIR ?? path.join(repoRoot, "docs", "Resources", "schemas"));
  const port = Number.parseInt(process.env.AIAGMW_PORT ?? process.env.PORT ?? "3000", 10);
  const akdbUrl = process.env.AIAGMW_AKDB_URL ?? "http://127.0.0.1:8787";
  const akdbProjectId = process.env.AIAGMW_AKDB_PROJECT_ID ?? "tiny-tool-development";
  const akdbExportRoot = path.resolve(
    process.env.AIAGMW_AKDB_EXPORT_ROOT ?? path.join(repoRoot, "exports", "akdb-staging")
  );
  const connectorsEnabled = (process.env.AIAGMW_CONNECTORS_ENABLED ?? "")
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);

  return {
    host: process.env.AIAGMW_HOST ?? "127.0.0.1",
    port: Number.isFinite(port) ? port : 3000,
    repoRoot,
    workspaceRoot,
    workspacesParent,
    schemaDir,
    akdbUrl,
    akdbProjectId,
    connectorsEnabled,
    akdbExportRoot
  };
}

export function resolveWorkspacePath(parent: string, requestedPath: string): string {
  const normalized = requestedPath.trim();
  if (!normalized) {
    throw new Error("Workspace path is required.");
  }
  const resolvedParent = path.resolve(parent);
  const resolved = path.isAbsolute(normalized) ? path.resolve(normalized) : path.resolve(resolvedParent, normalized);
  if (resolved !== resolvedParent && !resolved.startsWith(`${resolvedParent}${path.sep}`)) {
    throw new Error(`Workspace path escapes allowed parent: ${resolved}`);
  }
  return resolved;
}
