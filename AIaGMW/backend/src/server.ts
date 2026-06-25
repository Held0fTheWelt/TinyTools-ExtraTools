import cors from "@fastify/cors";
import Fastify from "fastify";
import { z } from "zod";
import { getConfig, resolveWorkspacePath } from "./config";
import { WorkspaceService } from "./workspaceService";

const modelTypeEnum = z.enum([
  "class-model",
  "component-model",
  "package-model",
  "sequence-model",
  "state-model",
  "activity-model",
  "deployment-model",
  "mixed-model"
]);

const diagramTypeEnum = z.enum(["class", "component", "package", "sequence", "state", "activity", "deployment", "mixed"]);

const elementKindEnum = z.enum([
  "class",
  "abstract_class",
  "interface",
  "enum",
  "component",
  "package",
  "layer",
  "module",
  "service",
  "subsystem",
  "actor",
  "node",
  "artifact",
  "note",
  "boundary",
  "lifeline",
  "activation",
  "fragment",
  "state_node",
  "pseudostate",
  "final_state",
  "action",
  "decision",
  "merge",
  "fork",
  "join",
  "deployment_spec"
]);

const relationKindEnum = z.enum([
  "association",
  "dependency",
  "inheritance",
  "implementation",
  "composition",
  "aggregation",
  "realization",
  "containment",
  "uses",
  "creates",
  "owns",
  "publishes",
  "subscribes",
  "calls",
  "sync_message",
  "async_message",
  "reply",
  "destroy",
  "transition",
  "control_flow",
  "object_flow",
  "deploy",
  "communicate"
]);

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

const app = Fastify({
  logger: true
});

await app.register(cors, {
  origin: true
});

app.get("/api/health", async () => ({
  ok: true,
  name: "AIaGMW backend",
  workspaceRoot: config.workspaceRoot,
  schemaDir: config.schemaDir
}));

app.get("/api/workspace/info", async () => service.info());
app.post("/api/workspace/open", async (request, reply) => {
  const body = z.object({ path: z.string().min(1) }).parse(request.body);
  try {
    const root = resolveWorkspacePath(config.workspacesParent, body.path);
    return await service.openWorkspace(root);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not open workspace." });
  }
});
app.post("/api/workspace/create", async (request, reply) => {
  const body = z
    .object({
      path: z.string().min(1),
      id: z.string().min(1),
      name: z.string().min(1),
      description: z.string().optional()
    })
    .parse(request.body);
  try {
    const root = resolveWorkspacePath(config.workspacesParent, body.path);
    return await service.createWorkspace({ root, id: body.id, name: body.name, description: body.description });
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not create workspace." });
  }
});
app.get("/api/workspace/models", async () => service.models());
app.get("/api/workspace/diagrams", async () => service.diagrams());
app.get("/api/workspace/index", async () => (await service.info()).index);
app.get("/api/proposals", async () => service.proposals());

app.get("/api/proposals/:proposalId", async (request, reply) => {
  const { proposalId } = z.object({ proposalId: z.string() }).parse(request.params);
  const proposal = await service.proposal(proposalId);
  if (!proposal) {
    return reply.code(404).send({ error: `Proposal ${proposalId} not found.` });
  }
  return proposal;
});

app.post("/api/proposals/:proposalId/preview", async (request, reply) => {
  const { proposalId } = z.object({ proposalId: z.string() }).parse(request.params);
  try {
    return await service.previewProposal(proposalId);
  } catch (error) {
    return reply.code(404).send({ error: error instanceof Error ? error.message : "Could not preview proposal." });
  }
});

app.post("/api/proposals/:proposalId/approve", async (request, reply) => {
  const { proposalId } = z.object({ proposalId: z.string() }).parse(request.params);
  const body = z
    .object({
      approvedBy: z.string().min(1),
      approvalNote: z.string().optional(),
      validationStatus: z.string().optional()
    })
    .parse(request.body ?? {});
  try {
    return {
      proposal: await service.approveProposal(proposalId, {
        approvedBy: body.approvedBy,
        approvedAt: new Date().toISOString(),
        approvalNote: body.approvalNote,
        validationStatus: body.validationStatus
      })
    };
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not approve proposal." });
  }
});

app.post("/api/proposals/:proposalId/apply", async (request, reply) => {
  const { proposalId } = z.object({ proposalId: z.string() }).parse(request.params);
  const body = z.object({ appliedBy: z.string().optional() }).parse(request.body ?? {});
  try {
    return await service.applyProposal(proposalId, body.appliedBy ?? "user");
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not apply proposal." });
  }
});

app.post("/api/validation/workspace", async () => service.validation());
app.get("/api/history/status", async () => (await service.info()).history);
app.post("/api/history/undo", async () => service.undo());
app.post("/api/history/redo", async () => service.redo());

app.post("/api/import/diagram/preview", async (request, reply) => {
  const body = z
    .object({
      format: z.enum(["plantuml", "mermaid"]),
      source: z.string().min(1),
      name: z.string().optional(),
      sourcePath: z.string().optional()
    })
    .parse(request.body);
  try {
    return await service.previewImportDiagram(body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not preview import." });
  }
});

app.post("/api/import/diagram", async (request, reply) => {
  const body = z
    .object({
      format: z.enum(["plantuml", "mermaid"]),
      source: z.string().min(1),
      name: z.string().optional(),
      sourcePath: z.string().optional()
    })
    .parse(request.body);
  try {
    return await service.importDiagram(body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not import diagram." });
  }
});

app.post("/api/export/diagrams/:diagramId", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z.object({ format: z.enum(["plantuml", "mermaid"]).default("plantuml") }).parse(request.body ?? {});
  try {
    return await service.exportDiagram(diagramId, body.format);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not export diagram." });
  }
});

app.post("/api/export/diagrams/:diagramId/image", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z
    .object({
      format: z.enum(["svg", "png"]),
      content: z.string().min(1)
    })
    .parse(request.body);
  try {
    return await service.exportDiagramImage(diagramId, body.format, body.content);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not export diagram image." });
  }
});

app.get("/api/models/:modelId", async (request, reply) => {
  const { modelId } = z.object({ modelId: z.string() }).parse(request.params);
  const model = await service.model(modelId);
  if (!model) {
    return reply.code(404).send({ error: `Model ${modelId} not found.` });
  }
  return model;
});

app.post("/api/models", async (request, reply) => {
  const body = z
    .object({
      name: z.string().min(1),
      modelType: modelTypeEnum
    })
    .parse(request.body);

  try {
    return { model: await service.createModel(body) };
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not create model." });
  }
});

app.patch("/api/models/:modelId/elements/:elementId", async (request, reply) => {
  const { modelId, elementId } = z.object({ modelId: z.string(), elementId: z.string() }).parse(request.params);
  const body = z.record(z.unknown()).parse(request.body);
  try {
    return { element: await service.updateElement(modelId, elementId, body) };
  } catch (error) {
    return reply.code(404).send({ error: error instanceof Error ? error.message : "Could not update element." });
  }
});

app.patch("/api/models/:modelId/relations/:relationId", async (request, reply) => {
  const { modelId, relationId } = z.object({ modelId: z.string(), relationId: z.string() }).parse(request.params);
  const body = z.record(z.unknown()).parse(request.body);
  try {
    return { relation: await service.updateRelation(modelId, relationId, body) };
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not update relation." });
  }
});

app.get("/api/diagrams/:diagramId", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const diagram = await service.diagram(diagramId);
  if (!diagram) {
    return reply.code(404).send({ error: `Diagram ${diagramId} not found.` });
  }
  return diagram;
});

app.post("/api/diagrams", async (request, reply) => {
  const body = z
    .object({
      name: z.string().min(1),
      diagramType: diagramTypeEnum,
      modelRefs: z.array(z.string()).optional()
    })
    .parse(request.body);

  try {
    return { diagram: await service.createDiagram(body) };
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not create diagram." });
  }
});

app.post("/api/diagrams/:diagramId/elements", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z
    .object({
      kind: elementKindEnum,
      name: z.string().min(1),
      modelId: z.string().optional(),
      x: z.number().optional(),
      y: z.number().optional(),
      width: z.number().optional(),
      height: z.number().optional()
    })
    .parse(request.body);

  try {
    return await service.createElement(diagramId, body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not create element." });
  }
});

app.post("/api/diagrams/:diagramId/element-refs", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z
    .object({
      elementId: z.string().min(1),
      x: z.number().optional(),
      y: z.number().optional(),
      width: z.number().optional(),
      height: z.number().optional()
    })
    .parse(request.body);

  try {
    return await service.addElementToDiagram(diagramId, body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not add element to diagram." });
  }
});

app.post("/api/diagrams/:diagramId/relations", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z
    .object({
      kind: relationKindEnum,
      from: z.string().min(1),
      to: z.string().min(1),
      name: z.string().optional(),
      modelId: z.string().optional()
    })
    .parse(request.body);

  try {
    return await service.createRelation(diagramId, body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not create relation." });
  }
});

app.post("/api/diagrams/:diagramId/relation-refs", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  const body = z
    .object({
      relationId: z.string().min(1),
      x: z.number().optional(),
      y: z.number().optional(),
      width: z.number().optional(),
      height: z.number().optional()
    })
    .parse(request.body);

  try {
    return await service.addRelationToDiagram(diagramId, body);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not add relation to diagram." });
  }
});

app.delete("/api/diagrams/:diagramId/elements/:elementId", async (request, reply) => {
  const { diagramId, elementId } = z.object({ diagramId: z.string(), elementId: z.string() }).parse(request.params);
  try {
    return await service.removeElementFromDiagram(diagramId, elementId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not remove element from diagram." });
  }
});

app.delete("/api/diagrams/:diagramId/relations/:relationId", async (request, reply) => {
  const { diagramId, relationId } = z.object({ diagramId: z.string(), relationId: z.string() }).parse(request.params);
  try {
    return await service.removeRelationFromDiagram(diagramId, relationId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not remove relation from diagram." });
  }
});

app.delete("/api/models/:modelId/elements/:elementId", async (request, reply) => {
  const { modelId, elementId } = z.object({ modelId: z.string(), elementId: z.string() }).parse(request.params);
  try {
    return await service.deleteElementFromModel(modelId, elementId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not delete element." });
  }
});

app.delete("/api/models/:modelId/relations/:relationId", async (request, reply) => {
  const { modelId, relationId } = z.object({ modelId: z.string(), relationId: z.string() }).parse(request.params);
  try {
    return await service.deleteRelationFromModel(modelId, relationId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not delete relation." });
  }
});

app.post("/api/diagrams/:diagramId/auto-layout", async (request, reply) => {
  const { diagramId } = z.object({ diagramId: z.string() }).parse(request.params);
  try {
    return await service.autoLayoutDiagram(diagramId);
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not auto layout diagram." });
  }
});

app.post("/api/diagrams/:diagramId/layout/nodes/:elementId", async (request, reply) => {
  const { diagramId, elementId } = z.object({ diagramId: z.string(), elementId: z.string() }).parse(request.params);
  const body = z
    .object({
      x: z.number().optional(),
      y: z.number().optional(),
      width: z.number().optional(),
      height: z.number().optional()
    })
    .parse(request.body);

  try {
    return { layout: await service.updateLayout(diagramId, elementId, body) };
  } catch (error) {
    return reply.code(400).send({ error: error instanceof Error ? error.message : "Could not update layout." });
  }
});

app.post("/api/agent-tools", async (request, reply) => {
  const body = z
    .object({
      tool: z.string(),
      arguments: z.record(z.unknown()).default({})
    })
    .parse(request.body);

  try {
    return await service.agentTool(body.tool, body.arguments);
  } catch (error) {
    return reply.code(400).send({ ok: false, error: error instanceof Error ? error.message : "Agent tool failed." });
  }
});

app.get("/api/agent-tools/log", async () => service.agentLog());

app.get("/api/connectors/status", async () => service.connectorStatus());

app.post("/api/connectors/akdb/context", async (request, reply) => {
  const body = z
    .object({
      task: z.string().min(1),
      projectId: z.string().optional()
    })
    .parse(request.body);
  const result = await service.akdbFetchContextPack(body.task, body.projectId);
  if (!result.ok) {
    return reply.code(result.diagnostics?.some((entry) => entry.code === "connector.disabled") ? 503 : 502).send(result);
  }
  return result;
});

app.get("/api/connectors/akdb/diagrams", async (request, reply) => {
  const query = z
    .object({
      kind: z.string().optional(),
      limit: z.coerce.number().int().positive().max(1000).optional(),
      query: z.string().optional()
    })
    .parse(request.query);
  const result = await service.akdbListDiagrams(query);
  if (!result.ok) {
    return reply.code(result.diagnostics?.some((entry) => entry.code === "connector.disabled") ? 503 : 502).send(result);
  }
  return result;
});

app.post("/api/connectors/akdb/import", async (request, reply) => {
  const body = z
    .object({
      diagramId: z.string().min(1),
      name: z.string().optional(),
      submit: z.boolean().optional()
    })
    .parse(request.body);
  const result = await service.akdbImportDiagram(body);
  if (!result.ok) {
    const disabled = "diagnostics" in result && result.diagnostics?.some((entry) => entry.code === "connector.disabled");
    return reply.code(disabled ? 503 : 502).send(result);
  }
  return result;
});

app.post("/api/proposals/:proposalId/reject", async (request, reply) => {
  const { proposalId } = z.object({ proposalId: z.string() }).parse(request.params);
  try {
    return { proposal: await service.rejectProposal(proposalId) };
  } catch (error) {
    return reply.code(404).send({ error: error instanceof Error ? error.message : "Could not reject proposal." });
  }
});

try {
  await app.listen({ host: config.host, port: config.port });
} catch (error) {
  app.log.error(error);
  process.exit(1);
}
