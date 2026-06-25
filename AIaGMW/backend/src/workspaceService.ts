import { watch, type FSWatcher } from "chokidar";
import {
  addElementToDiagram,
  addRelationToDiagram,
  applyPatch,
  approveProposal,
  createDiagram,
  createElementInDiagram,
  createModel,
  createRelationInDiagram,
  createWorkspace as scaffoldWorkspace,
  deleteElementFromModel,
  deleteRelationFromModel,
  generateDiff,
  getDiagramDetail,
  getElementContext,
  importDiagramSource,
  exportDiagramSource,
  exportDiagramImage as saveDiagramImage,
  importDiagramAsPatch,
  previewImportDiagramPatch,
  loadWorkspace,
  moveProposal,
  openWorkspace,
  previewPatch,
  removeElementFromDiagram,
  removeRelationFromDiagram,
  searchModel,
  simulatePatch,
  submitProposal,
  toWorkspaceInfo,
  applyAutoLayout,
  updateElement,
  updateRelation,
  updateNodeLayout,
  buildContextPack,
  validateModelScope,
  reviseProposal,
  type ApprovalRecord,
  type LoadWorkspaceOptions
} from "@aiagmw/core";
import type { DiagramExportFormat, DiagramImportFormat } from "@aiagmw/core";
import type { DiagramType, Diagnostic, ElementKind, ModelType, PatchProposal, RelationKind, UmlElement, UmlRelation } from "@aiagmw/shared";
import {
  getAkdbConnector,
  listConnectorDescriptors,
  probeConnectorStatus,
  type AkdbDiagramFilter,
  type ConnectorContext,
  type ConnectorSettings
} from "@aiagmw/connectors";
import { WorkspaceHistory } from "./workspaceHistory";

export interface AgentActionLogEntry {
  at: string;
  sessionId: string;
  tool: string;
  ok: boolean;
  error?: string;
}

export class WorkspaceService {
  private readonly history: WorkspaceHistory;
  private options: LoadWorkspaceOptions;
  private readonly connectorSettings: ConnectorSettings;
  private watcher: FSWatcher | null = null;
  private revision = 0;
  private lastExternalChangeAt: string | null = null;
  private agentActionLog: AgentActionLogEntry[] = [];
  private agentSessionId = `session-${Date.now()}`;

  constructor(initialOptions: LoadWorkspaceOptions, connectorSettings: ConnectorSettings) {
    this.options = initialOptions;
    this.connectorSettings = connectorSettings;
    this.history = new WorkspaceHistory(initialOptions.root);
    void this.startWatcher();
  }

  get currentOptions(): LoadWorkspaceOptions {
    return this.options;
  }

  get workspaceRevision(): number {
    return this.revision;
  }

  get externalChangeAt(): string | null {
    return this.lastExternalChangeAt;
  }

  async info() {
    const state = await loadWorkspace(this.options);
    const connectorDiagnostics = await this.collectConnectorDiagnostics();
    return {
      ...toWorkspaceInfo(state),
      history: this.history.status(),
      revision: this.revision,
      externalChangeAt: this.lastExternalChangeAt,
      connectorDiagnostics
    };
  }

  async switchWorkspace(root: string) {
    this.options = { ...this.options, root };
    this.history.setRoot(root);
    this.revision += 1;
    await this.restartWatcher();
    return this.info();
  }

  async createWorkspace(input: { root: string; id: string; name: string; description?: string }) {
    await scaffoldWorkspace(input);
    return this.switchWorkspace(input.root);
  }

  async openWorkspace(root: string) {
    await openWorkspace({ ...this.options, root });
    return this.switchWorkspace(root);
  }

  async models() {
    const state = await loadWorkspace(this.options);
    return {
      models: state.index.models,
      diagnostics: state.diagnostics
    };
  }

  async diagrams() {
    const state = await loadWorkspace(this.options);
    return {
      diagrams: state.index.diagrams,
      diagnostics: state.diagnostics
    };
  }

  async proposals() {
    const state = await loadWorkspace(this.options);
    return {
      proposals: state.index.proposals,
      diagnostics: state.diagnostics
    };
  }

  async proposal(proposalId: string) {
    const state = await loadWorkspace(this.options);
    const proposal = state.proposals.find((entry) => entry.data.id === proposalId);
    return proposal
      ? {
          proposal: proposal.data,
          path: proposal.relativePath
        }
      : null;
  }

  async previewProposal(proposalId: string) {
    return previewPatch(this.options, proposalId);
  }

  async approveProposal(proposalId: string, approval: ApprovalRecord) {
    return this.history.record("Approve proposal", () => approveProposal(this.options, proposalId, approval));
  }

  async applyProposal(proposalId: string, appliedBy = "user") {
    return this.history.record("Apply proposal", () => applyPatch(this.options, proposalId, appliedBy));
  }

  async model(modelId: string) {
    const state = await loadWorkspace(this.options);
    const model = state.models.find((entry) => entry.data.id === modelId);
    return model
      ? {
          model: model.data,
          path: model.relativePath,
          diagnostics: state.diagnostics.filter((diagnostic) => diagnostic.targetId === modelId)
        }
      : null;
  }

  async diagram(diagramId: string) {
    const state = await loadWorkspace(this.options);
    return getDiagramDetail(state, diagramId);
  }

  async validation() {
    const state = await loadWorkspace(this.options);
    return {
      diagnostics: state.diagnostics,
      index: state.index
    };
  }

  async createDiagram(input: { name: string; diagramType: DiagramType; modelRefs?: string[] }) {
    return this.history.record("Create diagram", () => createDiagram(this.options, input));
  }

  async createModel(input: { name: string; modelType: ModelType }) {
    return this.history.record("Create model", () => createModel(this.options, input));
  }

  async createElement(
    diagramId: string,
    input: {
      kind: ElementKind;
      name: string;
      modelId?: string;
      x?: number;
      y?: number;
      width?: number;
      height?: number;
    }
  ) {
    return this.history.record("Create element", () => createElementInDiagram(this.options, diagramId, input));
  }

  async addElementToDiagram(
    diagramId: string,
    input: { elementId: string; x?: number; y?: number; width?: number; height?: number }
  ) {
    return this.history.record("Add element to diagram", () => addElementToDiagram(this.options, diagramId, input));
  }

  async addRelationToDiagram(
    diagramId: string,
    input: { relationId: string; x?: number; y?: number; width?: number; height?: number }
  ) {
    return this.history.record("Add relation to diagram", () => addRelationToDiagram(this.options, diagramId, input));
  }

  async createRelation(
    diagramId: string,
    input: {
      kind: RelationKind;
      from: string;
      to: string;
      name?: string;
      modelId?: string;
    }
  ) {
    return this.history.record("Create relation", () => createRelationInDiagram(this.options, diagramId, input));
  }

  async updateElement(modelId: string, elementId: string, updates: Partial<UmlElement>) {
    return this.history.record("Update element", () => updateElement(this.options, modelId, elementId, updates));
  }

  async updateRelation(modelId: string, relationId: string, updates: Partial<UmlRelation>) {
    return this.history.record("Update relation", () => updateRelation(this.options, modelId, relationId, updates));
  }

  async removeElementFromDiagram(diagramId: string, elementId: string) {
    return this.history.record("Remove element from diagram", () => removeElementFromDiagram(this.options, diagramId, elementId));
  }

  async removeRelationFromDiagram(diagramId: string, relationId: string) {
    return this.history.record("Remove relation from diagram", () => removeRelationFromDiagram(this.options, diagramId, relationId));
  }

  async deleteElementFromModel(modelId: string, elementId: string) {
    return this.history.record("Delete element from model", async () => {
      await deleteElementFromModel(this.options, modelId, elementId);
      return { ok: true };
    });
  }

  async deleteRelationFromModel(modelId: string, relationId: string) {
    return this.history.record("Delete relation from model", async () => {
      await deleteRelationFromModel(this.options, modelId, relationId);
      return { ok: true };
    });
  }

  async updateLayout(diagramId: string, elementId: string, updates: { x?: number; y?: number; width?: number; height?: number }) {
    return this.history.record("Update layout", () => updateNodeLayout(this.options, diagramId, elementId, updates));
  }

  async autoLayoutDiagram(diagramId: string) {
    return this.history.record("Auto layout diagram", () => applyAutoLayout(this.options, diagramId));
  }

  async importDiagram(input: { format: DiagramImportFormat; source: string; name?: string; sourcePath?: string }) {
    return this.history.record("Import diagram", async () => {
      const result = await importDiagramAsPatch(this.options, input, true);
      return {
        proposal: result.proposal,
        summary: result.summary,
        conflicts: result.conflicts,
        imported: result.imported,
        applicable: result.applicable,
        preview: result.preview
      };
    });
  }

  async previewImportDiagram(input: { format: DiagramImportFormat; source: string; name?: string; sourcePath?: string }) {
    return previewImportDiagramPatch(this.options, input);
  }

  async importDiagramDirect(input: { format: DiagramImportFormat; source: string; name?: string; sourcePath?: string }) {
    return this.history.record("Import diagram", () => importDiagramSource(this.options, input));
  }

  async exportDiagram(diagramId: string, format: DiagramExportFormat) {
    return exportDiagramSource(this.options, diagramId, format);
  }

  async exportDiagramImage(diagramId: string, format: "svg" | "png", content: string) {
    return saveDiagramImage(this.options, diagramId, format, content);
  }

  async connectorStatus() {
    const descriptors = listConnectorDescriptors();
    const status = await probeConnectorStatus(this.connectorContext(), this.connectorSettings.connectorsEnabled);
    return {
      enabled: this.connectorSettings.connectorsEnabled,
      connectors: descriptors,
      status,
      diagnostics: this.statusDiagnostics(status)
    };
  }

  async akdbFetchContextPack(task: string, projectId?: string) {
    const connector = this.requireAkdbConnector();
    if (!connector) {
      return this.connectorDisabledResult("akdb");
    }
    return connector.fetchContextPack(task, projectId ?? this.connectorSettings.akdbProjectId);
  }

  async akdbListDiagrams(filter?: AkdbDiagramFilter) {
    const connector = this.requireAkdbConnector();
    if (!connector) {
      return this.connectorDisabledResult("akdb");
    }
    return connector.listNormativeDiagrams(this.connectorSettings.akdbProjectId, filter);
  }

  async akdbImportDiagram(input: { diagramId: string; name?: string; submit?: boolean }) {
    const connector = this.requireAkdbConnector();
    if (!connector) {
      return this.connectorDisabledResult("akdb");
    }

    const fetched = await connector.fetchDiagramSource(input.diagramId, this.connectorSettings.akdbProjectId);
    if (!fetched.ok || !fetched.data) {
      return fetched;
    }

    const importInput = {
      format: fetched.data.notation,
      source: fetched.data.source,
      name: input.name ?? fetched.data.title ?? fetched.data.diagramId,
      sourcePath: fetched.data.sourceKey ?? fetched.data.sourceUri
    };

    try {
      if (input.submit) {
        const result = await this.importDiagram(importInput);
        return {
          ok: true,
          data: result,
          provenance: fetched.provenance
        };
      }

      const preview = await this.previewImportDiagram(importInput);
      return {
        ok: true,
        data: preview,
        provenance: fetched.provenance
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not build import patch from AKDB diagram.";
      return {
        ok: false,
        error: message,
        diagnostics: [
          {
            level: "warning" as const,
            code: "connector.akdb.import_failed",
            message,
            category: "connector"
          }
        ],
        provenance: fetched.provenance
      };
    }
  }

  async akdbExportAndStage(input: { plantUmlSource: string; targetPath: string; diagramId?: string; sourceKey?: string }) {
    const connector = this.requireAkdbConnector();
    if (!connector) {
      return this.connectorDisabledResult("akdb");
    }

    return connector.exportAndStage(input.plantUmlSource, input.targetPath, {
      connector: "akdb",
      source: "workspace-export",
      projectId: this.connectorSettings.akdbProjectId,
      diagramId: input.diagramId,
      sourceKey: input.sourceKey,
      fetchedAt: new Date().toISOString()
    });
  }

  async agentTool(tool: string, args: Record<string, unknown>) {
    const state = await loadWorkspace(this.options);
    let result: { ok: boolean; result?: unknown; error?: string };

    try {
      switch (tool) {
        case "workspace_get_info":
          result = { ok: true, result: toWorkspaceInfo(state) };
          break;
        case "workspace_list_models":
          result = { ok: true, result: state.index.models };
          break;
        case "workspace_list_diagrams":
          result = { ok: true, result: state.index.diagrams };
          break;
        case "model_get": {
          const modelId = stringArg(args, "modelId");
          const model = state.models.find((entry) => entry.data.id === modelId);
          result = model ? { ok: true, result: model.data } : { ok: false, error: `Model ${modelId} not found.` };
          break;
        }
        case "diagram_get": {
          const diagramId = stringArg(args, "diagramId");
          const detail = getDiagramDetail(state, diagramId);
          result = detail ? { ok: true, result: detail } : { ok: false, error: `Diagram ${diagramId} not found.` };
          break;
        }
        case "model_search":
          result = { ok: true, result: searchModel(state, stringArg(args, "query")) };
          break;
        case "element_get_context": {
          const context = getElementContext(state, stringArg(args, "elementId"));
          result = context ? { ok: true, result: context } : { ok: false, error: "Element not found." };
          break;
        }
        case "proposal_submit_patch": {
          const proposal = patchArg(args, "patch");
          result = {
            ok: true,
            result: await this.history.record("Submit proposal", () => submitProposal(this.options, proposal))
          };
          break;
        }
        case "proposal_preview_patch": {
          const proposal = patchArg(args, "patch");
          const simulation = previewPatchFromProposal(state, proposal);
          result = { ok: true, result: simulation };
          break;
        }
        case "proposal_get_status": {
          const proposalId = stringArg(args, "proposalId");
          const proposal = state.index.proposals.find((entry) => entry.id === proposalId);
          result = proposal ? { ok: true, result: proposal } : { ok: false, error: `Proposal ${proposalId} not found.` };
          break;
        }
        case "proposal_apply_approved": {
          const proposalId = stringArg(args, "proposalId");
          const loaded = state.proposals.find((entry) => entry.data.id === proposalId);
          if (!loaded) {
            result = { ok: false, error: `Proposal ${proposalId} not found.` };
            break;
          }
          if (!loaded.data.metadata?.approval) {
            result = { ok: false, error: `Proposal ${proposalId} has no approval record.` };
            break;
          }
          result = {
            ok: true,
            result: await this.history.record("Apply proposal", () => applyPatch(this.options, proposalId, "agent"))
          };
          break;
        }
        case "model_validate": {
          const modelId = typeof args.modelId === "string" && args.modelId.trim() ? args.modelId : undefined;
          result = {
            ok: true,
            result: await validateModelScope(this.options, state, modelId)
          };
          break;
        }
        case "context_pack_build": {
          result = {
            ok: true,
            result: buildContextPack(state, {
              modelId: typeof args.modelId === "string" ? args.modelId : undefined,
              diagramId: typeof args.diagramId === "string" ? args.diagramId : undefined,
              elementIds: Array.isArray(args.elementIds)
                ? args.elementIds.filter((value): value is string => typeof value === "string")
                : undefined,
              query: typeof args.query === "string" ? args.query : undefined,
              maxElements: typeof args.maxElements === "number" ? args.maxElements : undefined,
              includeValidation: args.includeValidation !== false
            })
          };
          break;
        }
        case "proposal_revise": {
          const proposalId = stringArg(args, "proposalId");
          const loaded = state.proposals.find((entry) => entry.data.id === proposalId);
          if (!loaded) {
            result = { ok: false, error: `Proposal ${proposalId} not found.` };
            break;
          }
          const revised = reviseProposal(loaded.data, {
            title: typeof args.title === "string" ? args.title : undefined,
            intent: typeof args.intent === "string" ? args.intent : undefined,
            reasoningSummary: typeof args.reasoningSummary === "string" ? args.reasoningSummary : undefined,
            risk: typeof args.risk === "string" ? (args.risk as PatchProposal["risk"]) : undefined,
            replaceOperations: Array.isArray(args.replaceOperations)
              ? (args.replaceOperations as PatchProposal["operations"])
              : undefined,
            appendOperations: Array.isArray(args.appendOperations)
              ? (args.appendOperations as PatchProposal["operations"])
              : undefined,
            metadata: args.metadata && typeof args.metadata === "object" ? (args.metadata as Record<string, unknown>) : undefined
          });
          result = {
            ok: true,
            result: await this.history.record("Revise proposal", () => submitProposal(this.options, revised))
          };
          break;
        }
        default:
          result = { ok: false, error: `Unsupported tool: ${tool}` };
      }
    } catch (error) {
      result = { ok: false, error: error instanceof Error ? error.message : "Agent tool failed." };
    }

    this.agentActionLog.push({
      at: new Date().toISOString(),
      sessionId: this.agentSessionId,
      tool,
      ok: result.ok,
      error: result.error
    });

    return {
      ...result,
      sessionId: this.agentSessionId,
      capabilityManifest: {
        readTools: [
          "workspace_get_info",
          "workspace_list_models",
          "workspace_list_diagrams",
          "model_get",
          "diagram_get",
          "model_search",
          "element_get_context",
          "model_validate",
          "context_pack_build"
        ],
        proposalTools: [
          "proposal_submit_patch",
          "proposal_preview_patch",
          "proposal_get_status",
          "proposal_apply_approved",
          "proposal_revise"
        ],
        directFileWrite: false
      }
    };
  }

  agentLog() {
    return {
      sessionId: this.agentSessionId,
      entries: this.agentActionLog
    };
  }

  async close() {
    await this.watcher?.close();
    this.watcher = null;
  }

  async rejectProposal(proposalId: string) {
    return this.history.record("Reject proposal", () => moveProposal(this.options, proposalId, "rejected"));
  }

  async undo() {
    await this.history.undo();
    return this.info();
  }

  async redo() {
    await this.history.redo();
    return this.info();
  }

  private async startWatcher() {
    await this.restartWatcher();
  }

  private async restartWatcher() {
    await this.watcher?.close();
    this.watcher = watch(this.options.root, {
      ignoreInitial: true,
      awaitWriteFinish: { stabilityThreshold: 250, pollInterval: 100 }
    });
    this.watcher.on("all", () => {
      this.revision += 1;
      this.lastExternalChangeAt = new Date().toISOString();
    });
  }

  private connectorContext(): ConnectorContext {
    return {
      akdbUrl: this.connectorSettings.akdbUrl,
      akdbProjectId: this.connectorSettings.akdbProjectId,
      exportRoot: this.connectorSettings.akdbExportRoot
    };
  }

  private requireAkdbConnector() {
    return getAkdbConnector(this.connectorContext(), this.connectorSettings.connectorsEnabled);
  }

  private connectorDisabledResult(connectorId: string) {
    return {
      ok: false,
      error: `Connector ${connectorId} is not enabled.`,
      diagnostics: [
        {
          level: "info" as const,
          code: "connector.disabled",
          message: `Connector ${connectorId} is not enabled. Set AIAGMW_CONNECTORS_ENABLED=${connectorId}.`,
          category: "connector"
        }
      ]
    };
  }

  private statusDiagnostics(status: Awaited<ReturnType<typeof probeConnectorStatus>>): Diagnostic[] {
    return status
      .filter((entry) => entry.enabled && entry.reachable === false)
      .map((entry) => ({
        level: "warning" as const,
        code: "connector.unreachable",
        message: entry.error ?? `Connector ${entry.id} is unreachable.`,
        category: "connector"
      }));
  }

  private async collectConnectorDiagnostics(): Promise<Diagnostic[]> {
    if (this.connectorSettings.connectorsEnabled.length === 0) {
      return [];
    }

    try {
      const status = await probeConnectorStatus(this.connectorContext(), this.connectorSettings.connectorsEnabled);
      return this.statusDiagnostics(status);
    } catch (error) {
      return [
        {
          level: "warning" as const,
          code: "connector.probe_failed",
          message: error instanceof Error ? error.message : "Connector probe failed.",
          category: "connector"
        }
      ];
    }
  }
}

function stringArg(args: Record<string, unknown>, key: string): string {
  const value = args[key];
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`Expected string argument: ${key}`);
  }
  return value;
}

function patchArg(args: Record<string, unknown>, key: string): PatchProposal {
  const value = args[key];
  if (!value || typeof value !== "object") {
    throw new Error(`Expected patch argument: ${key}`);
  }
  return value as PatchProposal;
}

function previewPatchFromProposal(state: Awaited<ReturnType<typeof loadWorkspace>>, proposal: PatchProposal) {
  const simulation = simulatePatch(state, proposal);
  const diff = generateDiff(simulation.before, simulation.after, proposal);
  return {
    proposal,
    applicable: simulation.applicable,
    diagnostics: simulation.diagnostics,
    diff,
    operationErrors: simulation.operationErrors
  };
}
