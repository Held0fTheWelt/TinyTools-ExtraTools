import type { Diagnostic, PatchProposal, ProposalSummary, WorkspaceIndex } from "@aiagmw/shared";
import type { WorkspaceState } from "./workspace";
import { detectCycleDiagnostics } from "./validation/cycles";
import { endpointId } from "./workspaceHelpers";

interface Loaded<T> {
  data: T;
  file: string;
  relativePath: string;
}

export function reindexWorkspace(state: WorkspaceState): void {
  state.index = buildWorkspaceIndex(state.models, state.diagrams, state.proposals);
}

export function validateWorkspaceState(state: WorkspaceState): Diagnostic[] {
  return [
    ...validateWorkspaceReferences(state.models, state.diagrams, state.layouts),
    ...detectCycleDiagnostics(state.models)
  ];
}

function validateWorkspaceReferences(
  models: Array<Loaded<import("@aiagmw/shared").UmlModel>>,
  diagrams: Array<Loaded<import("@aiagmw/shared").UmlDiagram>>,
  layouts: Array<Loaded<import("@aiagmw/shared").UmlLayout>>
): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  const modelIds = new Set<string>();
  const elementIds = new Map<string, string>();
  const relationIds = new Map<string, string>();

  for (const model of models) {
    if (modelIds.has(model.data.id)) {
      diagnostics.push(duplicateDiagnostic(model.data.id, model.relativePath));
    }
    modelIds.add(model.data.id);

    for (const element of model.data.elements) {
      if (elementIds.has(element.id)) {
        diagnostics.push(duplicateDiagnostic(element.id, model.relativePath));
      }
      elementIds.set(element.id, model.data.id);
    }

    for (const relation of model.data.relations) {
      if (relationIds.has(relation.id)) {
        diagnostics.push(duplicateDiagnostic(relation.id, model.relativePath));
      }
      relationIds.set(relation.id, model.data.id);

      for (const [side, endpoint] of [
        ["source", relation.from],
        ["target", relation.to]
      ] as const) {
        if (!elementIds.has(endpointId(endpoint))) {
          diagnostics.push({
            level: "error",
            code: "reference.missing_endpoint",
            message: `Relation ${relation.id} has a missing ${side} endpoint: ${endpoint}.`,
            file: model.relativePath,
            targetId: relation.id,
            category: "reference"
          });
        }
      }
    }
  }

  for (const diagram of diagrams) {
    for (const modelRef of diagram.data.modelRefs) {
      if (!modelIds.has(modelRef)) {
        diagnostics.push({
          level: "error",
          code: "reference.missing_model",
          message: `Diagram ${diagram.data.id} references missing model ${modelRef}.`,
          file: diagram.relativePath,
          targetId: diagram.data.id,
          category: "reference"
        });
      }
    }

    for (const elementRef of diagram.data.elementRefs) {
      if (!elementIds.has(endpointId(elementRef))) {
        diagnostics.push({
          level: "error",
          code: "reference.missing_element",
          message: `Diagram ${diagram.data.id} references missing element ${elementRef}.`,
          file: diagram.relativePath,
          targetId: diagram.data.id,
          category: "reference"
        });
      }
    }

    for (const relationRef of diagram.data.relationRefs) {
      if (!relationIds.has(relationRef)) {
        diagnostics.push({
          level: "error",
          code: "reference.missing_relation",
          message: `Diagram ${diagram.data.id} references missing relation ${relationRef}.`,
          file: diagram.relativePath,
          targetId: diagram.data.id,
          category: "reference"
        });
      }
    }
  }

  for (const layout of layouts) {
    const diagram = diagrams.find((candidate) => candidate.data.id === layout.data.diagramId);
    if (!diagram) {
      diagnostics.push({
        level: "error",
        code: "reference.layout_missing_diagram",
        message: `Layout references missing diagram ${layout.data.diagramId}.`,
        file: layout.relativePath,
        targetId: layout.data.diagramId,
        category: "reference"
      });
      continue;
    }

    for (const nodeId of Object.keys(layout.data.nodes)) {
      if (!diagram.data.elementRefs.includes(nodeId)) {
        diagnostics.push({
          level: "warning",
          code: "reference.layout_node_not_in_diagram",
          message: `Layout node ${nodeId} is not present in diagram ${diagram.data.id}.`,
          file: layout.relativePath,
          targetId: nodeId,
          category: "reference"
        });
      }
    }
  }

  return diagnostics;
}

export function validateLoadedWorkspace(
  models: Array<Loaded<import("@aiagmw/shared").UmlModel>>,
  diagrams: Array<Loaded<import("@aiagmw/shared").UmlDiagram>>,
  layouts: Array<Loaded<import("@aiagmw/shared").UmlLayout>>
): Diagnostic[] {
  return [...validateWorkspaceReferences(models, diagrams, layouts), ...detectCycleDiagnostics(models)];
}

export function buildWorkspaceIndex(
  models: Array<Loaded<import("@aiagmw/shared").UmlModel>>,
  diagrams: Array<Loaded<import("@aiagmw/shared").UmlDiagram>>,
  proposals: Array<Loaded<PatchProposal>>
): WorkspaceIndex {
  const index: WorkspaceIndex = {
    models: models.map((entry) => summarizeModel(entry)),
    diagrams: diagrams.map((entry) => summarizeDiagram(entry)),
    proposals: proposals.map((entry) => summarizeProposal(entry)),
    elementToModel: {},
    elementToDiagrams: {},
    relationToModel: {},
    tags: {}
  };

  for (const model of models) {
    for (const element of model.data.elements) {
      index.elementToModel[element.id] = model.data.id;
      for (const tag of element.tags ?? []) {
        index.tags[tag] = [...(index.tags[tag] ?? []), element.id];
      }
    }
    for (const relation of model.data.relations) {
      index.relationToModel[relation.id] = model.data.id;
    }
  }

  for (const diagram of diagrams) {
    for (const elementId of diagram.data.elementRefs) {
      index.elementToDiagrams[elementId] = [...(index.elementToDiagrams[elementId] ?? []), diagram.data.id];
    }
  }

  return index;
}

function summarizeModel(entry: Loaded<import("@aiagmw/shared").UmlModel>) {
  return {
    id: entry.data.id,
    name: entry.data.name,
    modelType: entry.data.modelType,
    path: entry.relativePath,
    elementCount: entry.data.elements.length,
    relationCount: entry.data.relations.length,
    tags: metadataTags(entry.data.metadata)
  };
}

function summarizeDiagram(entry: Loaded<import("@aiagmw/shared").UmlDiagram>) {
  return {
    id: entry.data.id,
    name: entry.data.name,
    diagramType: entry.data.diagramType,
    path: entry.relativePath,
    modelRefs: entry.data.modelRefs,
    elementCount: entry.data.elementRefs.length,
    relationCount: entry.data.relationRefs.length,
    tags: metadataTags(entry.data.metadata)
  };
}

function summarizeProposal(entry: Loaded<PatchProposal>): ProposalSummary {
  return {
    id: entry.data.id,
    title: entry.data.title,
    status: entry.data.status,
    risk: entry.data.risk,
    path: entry.relativePath,
    operationCount: entry.data.operations.length
  };
}

function duplicateDiagnostic(id: string, file: string): Diagnostic {
  return {
    level: "error",
    code: "identity.duplicate_id",
    message: `Duplicate ID detected: ${id}.`,
    file,
    targetId: id,
    category: "identity"
  };
}

function metadataTags(metadata: Record<string, unknown> | undefined): string[] {
  const tags = metadata?.tags;
  return Array.isArray(tags) ? tags.filter((tag): tag is string => typeof tag === "string") : [];
}
