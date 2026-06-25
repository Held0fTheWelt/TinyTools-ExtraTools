import { describe, expect, it } from "vitest";
import { cp, mkdtemp, rm } from "node:fs/promises";
import path from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import Fastify from "fastify";
import cors from "@fastify/cors";
import { getConfig, resolveWorkspacePath } from "./config";
import { WorkspaceService } from "./workspaceService";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../..");
const sampleWorkspace = path.join(repoRoot, "sample-workspace");
const schemaDir = path.join(repoRoot, "docs", "Resources", "schemas");

async function buildTestApp(workspaceRoot: string) {
  const config = getConfig();
  const service = new WorkspaceService(
    { root: workspaceRoot, schemaDir: config.schemaDir },
    {
      akdbUrl: config.akdbUrl,
      akdbProjectId: config.akdbProjectId,
      akdbExportRoot: config.akdbExportRoot,
      connectorsEnabled: config.connectorsEnabled
    }
  );
  const app = Fastify();
  await app.register(cors, { origin: true });

  app.get("/api/health", async () => ({ ok: true }));
  app.get("/api/workspace/info", async () => service.info());
  app.post("/api/import/diagram/preview", async (request) => {
    const body = request.body as { format: "plantuml" | "mermaid"; source: string; name?: string };
    return service.previewImportDiagram(body);
  });
  app.post("/api/import/diagram", async (request) => {
    const body = request.body as { format: "plantuml" | "mermaid"; source: string; name?: string };
    return service.importDiagram(body);
  });
  app.post("/api/proposals/:proposalId/preview", async (request) => {
    const proposalId = (request.params as { proposalId: string }).proposalId;
    return service.previewProposal(proposalId);
  });
  app.post("/api/proposals/:proposalId/approve", async (request) => {
    const proposalId = (request.params as { proposalId: string }).proposalId;
    const body = (request.body ?? {}) as { approvedBy?: string };
    return {
      proposal: await service.approveProposal(proposalId, {
        approvedBy: body.approvedBy ?? "test",
        approvedAt: new Date().toISOString()
      })
    };
  });
  app.post("/api/proposals/:proposalId/apply", async (request) => {
    const proposalId = (request.params as { proposalId: string }).proposalId;
    return service.applyProposal(proposalId, "test");
  });
  app.post("/api/agent-tools", async (request) => {
    const body = request.body as { tool: string; arguments?: Record<string, unknown> };
    return service.agentTool(body.tool, body.arguments ?? {});
  });

  await app.ready();
  return { app, service, config };
}

describe("backend API integration", () => {
  it("previews and applies an approved proposal through REST surface", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-api-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const previewResponse = await app.inject({
        method: "POST",
        url: "/api/proposals/proposal.inventory.persistence-port/preview"
      });
      expect(previewResponse.statusCode).toBe(200);
      const preview = previewResponse.json() as { applicable: boolean };
      expect(preview.applicable).toBe(true);

      const approveResponse = await app.inject({
        method: "POST",
        url: "/api/proposals/proposal.inventory.persistence-port/approve",
        payload: { approvedBy: "integration-test" }
      });
      expect(approveResponse.statusCode).toBe(200);

      const applyResponse = await app.inject({
        method: "POST",
        url: "/api/proposals/proposal.inventory.persistence-port/apply",
        payload: { appliedBy: "integration-test" }
      });
      expect(applyResponse.statusCode).toBe(200);

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("blocks agent apply without approval", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-api-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const response = await app.inject({
        method: "POST",
        url: "/api/agent-tools",
        payload: {
          tool: "proposal_apply_approved",
          arguments: { proposalId: "proposal.inventory.persistence-port" }
        }
      });
      const body = response.json() as { ok: boolean; error?: string };
      expect(body.ok).toBe(false);
      expect(body.error).toMatch(/approval record/i);

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("resolves workspace paths under workspaces parent", () => {
    const parent = path.join(repoRoot, "workspaces");
    const resolved = resolveWorkspacePath(parent, "demo");
    expect(resolved).toBe(path.join(parent, "demo"));
  });

  it("previews import as patch without creating pending proposal", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-import-preview-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const response = await app.inject({
        method: "POST",
        url: "/api/import/diagram/preview",
        payload: {
          format: "plantuml",
          name: "Billing Import",
          source: "@startuml\nclass Invoice\n@enduml"
        }
      });

      expect(response.statusCode).toBe(200);
      const body = response.json() as { applicable: boolean; proposal: { status: string } };
      expect(body.applicable).toBe(true);
      expect(body.proposal.status).toBe("pending");

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("creates pending import proposal through import endpoint", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-import-proposal-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const response = await app.inject({
        method: "POST",
        url: "/api/import/diagram",
        payload: {
          format: "plantuml",
          name: "Billing Import",
          source: "@startuml\nclass Invoice\n@enduml"
        }
      });

      expect(response.statusCode).toBe(200);
      const body = response.json() as { summary: { status: string }; proposal: { id: string } };
      expect(body.summary.status).toBe("pending");

      const info = await app.inject({ method: "GET", url: "/api/workspace/info" });
      const proposals = (info.json() as { index: { proposals: Array<{ id: string }> } }).index.proposals;
      expect(proposals.some((proposal) => proposal.id === body.proposal.id)).toBe(true);

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("exposes model_validate and context_pack_build agent tools", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-agent-tools-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const validateResponse = await app.inject({
        method: "POST",
        url: "/api/agent-tools",
        payload: { tool: "model_validate", arguments: { modelId: "model.inventory" } }
      });
      const validateBody = validateResponse.json() as { ok: boolean; result: { scope: string; diagnostics: unknown[] } };
      expect(validateBody.ok).toBe(true);
      expect(validateBody.result.scope).toBe("model");

      const contextResponse = await app.inject({
        method: "POST",
        url: "/api/agent-tools",
        payload: {
          tool: "context_pack_build",
          arguments: { diagramId: "diagram.inventory.class", includeValidation: true }
        }
      });
      const contextBody = contextResponse.json() as {
        ok: boolean;
        result: { workspaceSummary: { modelCount: number }; selectedElements: unknown[] };
      };
      expect(contextBody.ok).toBe(true);
      expect(contextBody.result.workspaceSummary.modelCount).toBeGreaterThan(0);
      expect(contextBody.result.selectedElements.length).toBeGreaterThan(0);

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("supports proposal_revise agent tool", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-proposal-revise-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const { app, service } = await buildTestApp(root);

      const response = await app.inject({
        method: "POST",
        url: "/api/agent-tools",
        payload: {
          tool: "proposal_revise",
          arguments: {
            proposalId: "proposal.inventory.persistence-port",
            title: "Revised persistence port proposal",
            appendOperations: []
          }
        }
      });
      const body = response.json() as { ok: boolean; result?: { title: string } };
      expect(body.ok).toBe(true);
      expect(body.result?.title).toBe("Revised persistence port proposal");

      await app.close();
      await service.close();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
