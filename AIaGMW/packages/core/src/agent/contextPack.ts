import type { Diagnostic, PatchOperation, PatchProposal, PatchRisk } from "@aiagmw/shared";
import { getDiagramDetail, getElementContext, type WorkspaceState } from "../workspace";
import { validateWorkspaceState } from "../workspaceIndex";
import { SchemaValidator, type SchemaKind } from "../schemaValidation";
import type { LoadWorkspaceOptions } from "../workspace";

export interface ContextPackRequest {
  modelId?: string;
  diagramId?: string;
  elementIds?: string[];
  query?: string;
  maxElements?: number;
  includeValidation?: boolean;
}

export interface ContextPack {
  workspaceSummary: {
    id: string | null;
    name: string | null;
    modelCount: number;
    diagramCount: number;
    proposalCount: number;
  };
  relevantModels: Array<{ id: string; name: string; modelType: string; elementCount: number; relationCount: number }>;
  relevantDiagrams: Array<{ id: string; name: string; diagramType: string; elementCount: number; relationCount: number }>;
  selectedElements: Array<Record<string, unknown>>;
  validationDiagnostics: Diagnostic[];
  recentHistory: Array<{ id: string; title: string; status: string; path: string }>;
}

export function buildContextPack(state: WorkspaceState, request: ContextPackRequest = {}): ContextPack {
  const maxElements = request.maxElements ?? 20;
  const selectedIds = new Set(request.elementIds ?? []);
  const relevantModelIds = new Set<string>();
  const relevantDiagramIds = new Set<string>();

  if (request.modelId) {
    relevantModelIds.add(request.modelId);
  }
  if (request.diagramId) {
    relevantDiagramIds.add(request.diagramId);
    const detail = getDiagramDetail(state, request.diagramId);
    for (const model of detail?.models ?? []) {
      relevantModelIds.add(model.id);
    }
  }

  if (request.query?.trim()) {
    const normalized = request.query.trim().toLowerCase();
    for (const model of state.models) {
      for (const element of model.data.elements) {
        const haystack = [element.id, element.name, element.kind, ...(element.tags ?? [])].join(" ").toLowerCase();
        if (haystack.includes(normalized)) {
          selectedIds.add(element.id);
          relevantModelIds.add(model.data.id);
          for (const diagramId of state.index.elementToDiagrams[element.id] ?? []) {
            relevantDiagramIds.add(diagramId);
          }
        }
      }
    }
  }

  for (const elementId of selectedIds) {
    const context = getElementContext(state, elementId);
    if (!context) {
      continue;
    }
    relevantModelIds.add(context.modelId);
    for (const diagramId of context.diagrams) {
      relevantDiagramIds.add(diagramId);
    }
  }

  const selectedElements = [...selectedIds]
    .slice(0, maxElements)
    .map((elementId) => getElementContext(state, elementId))
    .filter((context): context is NonNullable<typeof context> => Boolean(context))
    .map((context) => ({
      id: context.element.id,
      name: context.element.name,
      kind: context.element.kind,
      modelId: context.modelId,
      diagrams: context.diagrams,
      relations: context.relations,
      diagnostics: context.diagnostics
    }));

  if (selectedElements.length === 0 && request.diagramId) {
    const detail = getDiagramDetail(state, request.diagramId);
    for (const element of (detail?.elements ?? []).slice(0, maxElements)) {
      selectedElements.push({
        id: element.id,
        name: element.name,
        kind: element.kind,
        modelId: element.modelId,
        diagrams: [request.diagramId],
        relations: [],
        diagnostics: []
      });
    }
  }

  const validationDiagnostics = request.includeValidation === false ? [] : validateWorkspaceState(state);

  return {
    workspaceSummary: {
      id: state.manifest?.id ?? null,
      name: state.manifest?.name ?? null,
      modelCount: state.index.models.length,
      diagramCount: state.index.diagrams.length,
      proposalCount: state.index.proposals.length
    },
    relevantModels: state.index.models
      .filter((model) => relevantModelIds.size === 0 || relevantModelIds.has(model.id))
      .slice(0, 10)
      .map((model) => ({
        id: model.id,
        name: model.name,
        modelType: model.modelType,
        elementCount: model.elementCount,
        relationCount: model.relationCount
      })),
    relevantDiagrams: state.index.diagrams
      .filter((diagram) => relevantDiagramIds.size === 0 || relevantDiagramIds.has(diagram.id))
      .slice(0, 10)
      .map((diagram) => ({
        id: diagram.id,
        name: diagram.name,
        diagramType: diagram.diagramType,
        elementCount: diagram.elementCount,
        relationCount: diagram.relationCount
      })),
    selectedElements,
    validationDiagnostics: validationDiagnostics.slice(0, 50),
    recentHistory: state.index.proposals.slice(0, 10).map((proposal) => ({
      id: proposal.id,
      title: proposal.title,
      status: proposal.status,
      path: proposal.path
    }))
  };
}

export interface ModelValidationResult {
  scope: "workspace" | "model";
  modelId?: string;
  diagnostics: Diagnostic[];
}

export async function validateModelScope(
  options: LoadWorkspaceOptions,
  state: WorkspaceState,
  modelId?: string
): Promise<ModelValidationResult> {
  const validator = await SchemaValidator.create(options.schemaDir);
  const diagnostics = [...validateWorkspaceState(state)];

  if (modelId) {
    const model = state.models.find((entry) => entry.data.id === modelId);
    if (!model) {
      return {
        scope: "model",
        modelId,
        diagnostics: [
          {
            level: "error",
            code: "model.not_found",
            message: `Model ${modelId} was not found.`,
            targetId: modelId,
            category: "validation"
          }
        ]
      };
    }

    diagnostics.push(...validator.validate("model", model.data, model.relativePath));
    return { scope: "model", modelId, diagnostics };
  }

  for (const model of state.models) {
    diagnostics.push(...validator.validate("model", model.data, model.relativePath));
  }
  for (const diagram of state.diagrams) {
    diagnostics.push(...validator.validate("diagram", diagram.data, diagram.relativePath));
  }
  for (const layout of state.layouts) {
    diagnostics.push(...validator.validate("layout", layout.data, layout.relativePath));
  }
  if (state.manifest) {
    diagnostics.push(...validator.validate("workspace", state.manifest));
  }

  return { scope: "workspace", diagnostics };
}

export interface ProposalReviseInput {
  title?: string;
  intent?: string;
  reasoningSummary?: string;
  risk?: PatchRisk;
  replaceOperations?: PatchOperation[];
  appendOperations?: PatchOperation[];
  metadata?: Record<string, unknown>;
}

export function reviseProposal(proposal: PatchProposal, revisions: ProposalReviseInput): PatchProposal {
  const operations = revisions.replaceOperations
    ? [...revisions.replaceOperations]
    : [...proposal.operations, ...(revisions.appendOperations ?? [])];

  return {
    ...proposal,
    title: revisions.title ?? proposal.title,
    intent: revisions.intent ?? proposal.intent,
    reasoningSummary: revisions.reasoningSummary ?? proposal.reasoningSummary,
    risk: revisions.risk ?? proposal.risk,
    operations,
    metadata: {
      ...proposal.metadata,
      ...revisions.metadata,
      revisedAt: new Date().toISOString()
    }
  };
}

export function schemaKindForScope(scope: "workspace" | "model"): SchemaKind {
  return scope === "model" ? "model" : "workspace";
}
