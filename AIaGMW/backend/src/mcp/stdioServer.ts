import { createInterface } from "node:readline";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getConfig } from "../config";
import { WorkspaceService } from "../workspaceService";

interface JsonRpcRequest {
  jsonrpc?: string;
  id?: string | number | null;
  method?: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

function writeResponse(response: JsonRpcResponse): void {
  process.stdout.write(`${JSON.stringify(response)}\n`);
}

function invalidRequest(id: string | number | null, message: string): JsonRpcResponse {
  return {
    jsonrpc: "2.0",
    id,
    error: { code: -32600, message }
  };
}

async function handleRequest(service: WorkspaceService, request: JsonRpcRequest): Promise<JsonRpcResponse> {
  const id = request.id ?? null;
  if (request.jsonrpc !== "2.0" || typeof request.method !== "string") {
    return invalidRequest(id, "Invalid JSON-RPC request.");
  }

  if (request.method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        serverInfo: { name: "aiagmw-mcp-stdio", version: "0.1.0" },
        capabilities: { tools: {} }
      }
    };
  }

  if (request.method === "tools/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        tools: [
          { name: "workspace_get_info", description: "Get workspace summary" },
          { name: "model_validate", description: "Validate one model or the whole workspace" },
          { name: "context_pack_build", description: "Build a compact context pack" },
          { name: "proposal_submit_patch", description: "Submit a patch proposal" },
          { name: "proposal_preview_patch", description: "Preview a patch proposal" },
          { name: "proposal_revise", description: "Revise an existing proposal" }
        ]
      }
    };
  }

  if (request.method === "tools/call") {
    const params = request.params ?? {};
    const tool = typeof params.name === "string" ? params.name : "";
    const args =
      params.arguments && typeof params.arguments === "object"
        ? (params.arguments as Record<string, unknown>)
        : {};
    if (!tool) {
      return invalidRequest(id, "tools/call requires params.name.");
    }
    const result = await service.agentTool(tool, args);
    return { jsonrpc: "2.0", id, result };
  }

  if (request.method === "agent_tool") {
    const params = request.params ?? {};
    const tool = typeof params.tool === "string" ? params.tool : "";
    const args =
      params.arguments && typeof params.arguments === "object"
        ? (params.arguments as Record<string, unknown>)
        : {};
    if (!tool) {
      return invalidRequest(id, "agent_tool requires params.tool.");
    }
    const result = await service.agentTool(tool, args);
    return { jsonrpc: "2.0", id, result };
  }

  return invalidRequest(id, `Unsupported method: ${request.method}`);
}

export async function runStdioServer(): Promise<void> {
  const config = getConfig();
  const service = new WorkspaceService(
    {
      root: config.workspaceRoot,
      schemaDir: config.schemaDir
    },
    {
      akdbUrl: config.akdbUrl,
      akdbProjectId: config.akdbProjectId,
      akdbExportRoot: config.akdbExportRoot,
      connectorsEnabled: config.connectorsEnabled
    }
  );

  const rl = createInterface({ input: process.stdin, terminal: false });
  rl.on("line", (line) => {
    void (async () => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }
      try {
        const request = JSON.parse(trimmed) as JsonRpcRequest;
        const response = await handleRequest(service, request);
        writeResponse(response);
      } catch (error) {
        writeResponse({
          jsonrpc: "2.0",
          id: null,
          error: {
            code: -32700,
            message: error instanceof Error ? error.message : "Parse error."
          }
        });
      }
    })();
  });

  rl.on("close", async () => {
    await service.close();
    process.exit(0);
  });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  runStdioServer().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
