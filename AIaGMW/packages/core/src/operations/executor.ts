import type { Diagnostic, NodeLayout, PatchOperation, UmlElement, UmlRelation } from "@aiagmw/shared";
import type { WorkspaceState } from "../workspace";
import { endpointId, findElement, findRelation } from "../workspaceHelpers";

export interface OperationError {
  op: string;
  message: string;
}

export interface OperationBatchResult {
  errors: OperationError[];
}

export function applyOperations(state: WorkspaceState, operations: PatchOperation[]): OperationBatchResult {
  const errors: OperationError[] = [];

  for (const operation of operations) {
    try {
      applyOperation(state, operation);
    } catch (error) {
      errors.push({
        op: operation.op,
        message: error instanceof Error ? error.message : "Operation failed."
      });
    }
  }

  return { errors };
}

function applyOperation(state: WorkspaceState, operation: PatchOperation): void {
  switch (operation.op) {
    case "add_element":
      return opAddElement(state, operation);
    case "update_element":
      return opUpdateElement(state, operation);
    case "remove_element":
      return opRemoveElement(state, operation);
    case "add_relation":
      return opAddRelation(state, operation);
    case "update_relation":
      return opUpdateRelation(state, operation);
    case "remove_relation":
      return opRemoveRelation(state, operation);
    case "add_to_diagram":
      return opAddToDiagram(state, operation);
    case "remove_from_diagram":
      return opRemoveFromDiagram(state, operation);
    case "set_node_position":
    case "set_node_size":
      return opSetNodeLayout(state, operation);
    case "create_model":
      return opCreateModel(state, operation);
    case "create_diagram":
      return opCreateDiagram(state, operation);
    case "update_diagram":
      return opUpdateDiagram(state, operation);
    case "rename_element":
      return opRenameElement(state, operation);
    case "move_element_to_model":
      return opMoveElementToModel(state, operation);
    case "set_edge_route":
      return opSetEdgeRoute(state, operation);
    case "apply_layout":
      return opApplyLayout(state, operation);
    case "add_note":
      return opAddNote(state, operation);
    case "add_tag":
      return opAddTag(state, operation);
    case "remove_tag":
      return opRemoveTag(state, operation);
    case "link_decision":
      return opLinkDecision(state, operation);
    case "link_practice":
      return opLinkPractice(state, operation);
    case "set_status":
      return opSetStatus(state, operation);
    default:
      throw new Error(`Unsupported operation: ${operation.op}`);
  }
}

function requireModel(state: WorkspaceState, modelId: string) {
  const model = state.models.find((entry) => entry.data.id === modelId);
  if (!model) {
    throw new Error(`Model ${modelId} was not found.`);
  }
  return model;
}

function requireDiagram(state: WorkspaceState, diagramId: string) {
  const diagram = state.diagrams.find((entry) => entry.data.id === diagramId);
  if (!diagram) {
    throw new Error(`Diagram ${diagramId} was not found.`);
  }
  return diagram;
}

function requireLayout(state: WorkspaceState, diagramId: string) {
  let layout = state.layouts.find((entry) => entry.data.diagramId === diagramId);
  if (!layout) {
    layout = {
      data: {
        schema: "umllayout.v1",
        diagramId,
        nodes: {},
        edges: {}
      },
      file: "",
      relativePath: ""
    };
    state.layouts.push(layout);
  }
  return layout;
}

function opAddElement(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  if (!modelId) {
    throw new Error("add_element requires modelId.");
  }
  const element = operation.element as UmlElement | undefined;
  if (!element?.id || !element.kind || !element.name) {
    throw new Error("add_element requires a complete element.");
  }

  const model = requireModel(state, modelId);
  if (model.data.elements.some((candidate) => candidate.id === element.id)) {
    throw new Error(`Element ${element.id} already exists in model ${modelId}.`);
  }

  model.data.elements.push({
    responsibilities: [],
    properties: [],
    methods: [],
    constraints: [],
    tags: [],
    ...element,
    id: element.id,
    kind: element.kind,
    name: element.name
  });
}

function opUpdateElement(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  const elementId = operation.elementId;
  if (!modelId || !elementId) {
    throw new Error("update_element requires modelId and elementId.");
  }

  const model = requireModel(state, modelId);
  const element = model.data.elements.find((candidate) => candidate.id === elementId);
  if (!element) {
    throw new Error(`Element ${elementId} was not found in model ${modelId}.`);
  }

  Object.assign(element, {
    ...operation.updates,
    ...operation.element,
    id: element.id
  });
}

function opRemoveElement(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  const elementId = operation.elementId;
  if (!modelId || !elementId) {
    throw new Error("remove_element requires modelId and elementId.");
  }

  const model = requireModel(state, modelId);
  const normalized = endpointId(elementId);
  const removedRelationIds = new Set(
    model.data.relations
      .filter((relation) => endpointId(relation.from) === normalized || endpointId(relation.to) === normalized)
      .map((relation) => relation.id)
  );

  model.data.elements = model.data.elements.filter((element) => element.id !== normalized);
  model.data.relations = model.data.relations.filter((relation) => !removedRelationIds.has(relation.id));

  for (const diagram of state.diagrams) {
    diagram.data.elementRefs = diagram.data.elementRefs.filter((id) => id !== normalized);
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => !removedRelationIds.has(id));
  }

  for (const layout of state.layouts) {
    delete layout.data.nodes[normalized];
    for (const relationId of removedRelationIds) {
      delete layout.data.edges[relationId];
    }
  }
}

function opAddRelation(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  if (!modelId) {
    throw new Error("add_relation requires modelId.");
  }
  const relation = operation.relation as UmlRelation | undefined;
  if (!relation?.id || !relation.kind || !relation.from || !relation.to) {
    throw new Error("add_relation requires a complete relation.");
  }

  const model = requireModel(state, modelId);
  if (model.data.relations.some((candidate) => candidate.id === relation.id)) {
    throw new Error(`Relation ${relation.id} already exists in model ${modelId}.`);
  }

  const from = endpointId(relation.from);
  const to = endpointId(relation.to);
  if (!findElement(state, from)) {
    throw new Error(`Relation source ${from} was not found.`);
  }
  if (!findElement(state, to)) {
    throw new Error(`Relation target ${to} was not found.`);
  }

  model.data.relations.push({
    stereotypes: [],
    tags: [],
    ...relation,
    id: relation.id,
    kind: relation.kind,
    from,
    to
  });
}

function opUpdateRelation(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  const relationId = operation.relationId;
  if (!modelId || !relationId) {
    throw new Error("update_relation requires modelId and relationId.");
  }

  const model = requireModel(state, modelId);
  const relation = model.data.relations.find((candidate) => candidate.id === relationId);
  if (!relation) {
    throw new Error(`Relation ${relationId} was not found in model ${modelId}.`);
  }

  const nextFrom = operation.updates?.from ? endpointId(String(operation.updates.from)) : relation.from;
  const nextTo = operation.updates?.to ? endpointId(String(operation.updates.to)) : relation.to;
  if (!findElement(state, nextFrom)) {
    throw new Error(`Relation source ${nextFrom} was not found.`);
  }
  if (!findElement(state, nextTo)) {
    throw new Error(`Relation target ${nextTo} was not found.`);
  }

  Object.assign(relation, {
    ...operation.updates,
    ...operation.relation,
    id: relation.id,
    from: nextFrom,
    to: nextTo
  });
}

function opRemoveRelation(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  const relationId = operation.relationId;
  if (!modelId || !relationId) {
    throw new Error("remove_relation requires modelId and relationId.");
  }

  const model = requireModel(state, modelId);
  model.data.relations = model.data.relations.filter((relation) => relation.id !== relationId);

  for (const diagram of state.diagrams) {
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => id !== relationId);
  }

  for (const layout of state.layouts) {
    delete layout.data.edges[relationId];
  }
}

function opAddToDiagram(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  if (!diagramId) {
    throw new Error("add_to_diagram requires diagramId.");
  }

  const diagram = requireDiagram(state, diagramId);
  const elementId = operation.elementId;
  const relationId = operation.relationId;

  if (elementId) {
    const resolved = findElement(state, elementId);
    if (!resolved) {
      throw new Error(`Element ${elementId} was not found.`);
    }
    if (!diagram.data.modelRefs.includes(resolved.model.data.id)) {
      throw new Error(`Element ${elementId} belongs to an unlinked model.`);
    }
    if (!diagram.data.elementRefs.includes(resolved.element.id)) {
      diagram.data.elementRefs.push(resolved.element.id);
    }
    return;
  }

  if (relationId) {
    const resolved = findRelation(state, relationId);
    if (!resolved) {
      throw new Error(`Relation ${relationId} was not found.`);
    }
    if (!diagram.data.modelRefs.includes(resolved.model.data.id)) {
      throw new Error(`Relation ${relationId} belongs to an unlinked model.`);
    }
    if (!diagram.data.relationRefs.includes(resolved.relation.id)) {
      diagram.data.relationRefs.push(resolved.relation.id);
    }
    const from = endpointId(resolved.relation.from);
    const to = endpointId(resolved.relation.to);
    for (const id of [from, to]) {
      if (!diagram.data.elementRefs.includes(id)) {
        diagram.data.elementRefs.push(id);
      }
    }
    return;
  }

  throw new Error("add_to_diagram requires elementId or relationId.");
}

function opRemoveFromDiagram(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  if (!diagramId) {
    throw new Error("remove_from_diagram requires diagramId.");
  }

  const diagram = requireDiagram(state, diagramId);
  const layout = requireLayout(state, diagramId);
  const elementId = operation.elementId;
  const relationId = operation.relationId;

  if (relationId) {
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => id !== relationId);
    delete layout.data.edges[relationId];
    return;
  }

  if (elementId) {
    const normalized = endpointId(elementId);
    diagram.data.elementRefs = diagram.data.elementRefs.filter((id) => id !== normalized);
    const visibleElements = new Set(diagram.data.elementRefs);
    const removedRelationIds: string[] = [];
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => {
      const relation = findRelation(state, id)?.relation;
      const keep = relation ? visibleElements.has(endpointId(relation.from)) && visibleElements.has(endpointId(relation.to)) : false;
      if (!keep) {
        removedRelationIds.push(id);
      }
      return keep;
    });
    delete layout.data.nodes[normalized];
    for (const id of removedRelationIds) {
      delete layout.data.edges[id];
    }
    return;
  }

  throw new Error("remove_from_diagram requires elementId or relationId.");
}

function opSetNodeLayout(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  const elementId = operation.elementId;
  if (!diagramId || !elementId) {
    throw new Error("set_node_position requires diagramId and elementId.");
  }

  requireDiagram(state, diagramId);
  const layout = requireLayout(state, diagramId);
  const normalized = endpointId(elementId);
  const current = layout.data.nodes[normalized] ?? { x: 0, y: 0 };
  layout.data.nodes[normalized] = {
    ...current,
    ...operation.updates
  };
}

function opCreateModel(state: WorkspaceState, operation: PatchOperation): void {
  const model = operation.updates?.model as Record<string, unknown> | undefined;
  if (!model?.id || !model.name || !model.modelType) {
    throw new Error("create_model requires updates.model with id, name, and modelType.");
  }

  if (state.models.some((entry) => entry.data.id === model.id)) {
    throw new Error(`Model ${model.id} already exists.`);
  }

  state.models.push({
    data: {
      schema: "umlmodel.v1",
      id: String(model.id),
      name: String(model.name),
      modelType: model.modelType as never,
      elements: [],
      relations: [],
      metadata: (model.metadata as Record<string, unknown>) ?? {}
    },
    file: typeof operation.updates?.file === "string" ? operation.updates.file : "",
    relativePath: typeof operation.updates?.relativePath === "string" ? operation.updates.relativePath : ""
  });
}

function opCreateDiagram(state: WorkspaceState, operation: PatchOperation): void {
  const diagram = operation.updates?.diagram as Record<string, unknown> | undefined;
  if (!diagram?.id || !diagram.name || !diagram.diagramType) {
    throw new Error("create_diagram requires updates.diagram with id, name, and diagramType.");
  }

  if (state.diagrams.some((entry) => entry.data.id === diagram.id)) {
    throw new Error(`Diagram ${diagram.id} already exists.`);
  }

  const diagramFile = typeof operation.updates?.file === "string" ? operation.updates.file : "";
  const diagramRelativePath =
    typeof operation.updates?.relativePath === "string" ? operation.updates.relativePath : "";

  state.diagrams.push({
    data: {
      schema: "umldiagram.v1",
      id: String(diagram.id),
      name: String(diagram.name),
      diagramType: diagram.diagramType as never,
      modelRefs: Array.isArray(diagram.modelRefs) ? (diagram.modelRefs as string[]) : [],
      elementRefs: [],
      relationRefs: [],
      metadata: (diagram.metadata as Record<string, unknown>) ?? {}
    },
    file: diagramFile,
    relativePath: diagramRelativePath
  });

  state.layouts.push({
    data: {
      schema: "umllayout.v1",
      diagramId: String(diagram.id),
      nodes: {},
      edges: {}
    },
    file: typeof operation.updates?.layoutFile === "string" ? operation.updates.layoutFile : "",
    relativePath: typeof operation.updates?.layoutRelativePath === "string" ? operation.updates.layoutRelativePath : ""
  });
}

function opUpdateDiagram(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  if (!diagramId) {
    throw new Error("update_diagram requires diagramId.");
  }

  const diagram = requireDiagram(state, diagramId);
  Object.assign(diagram.data, {
    ...operation.updates,
    id: diagram.data.id,
    schema: diagram.data.schema
  });
}

function requireElement(state: WorkspaceState, modelId: string, elementId: string) {
  const model = requireModel(state, modelId);
  const normalized = endpointId(elementId);
  const element = model.data.elements.find((candidate) => candidate.id === normalized);
  if (!element) {
    throw new Error(`Element ${elementId} was not found in model ${modelId}.`);
  }
  return { model, element };
}

function requireRelation(state: WorkspaceState, modelId: string, relationId: string) {
  const model = requireModel(state, modelId);
  const relation = model.data.relations.find((candidate) => candidate.id === relationId);
  if (!relation) {
    throw new Error(`Relation ${relationId} was not found in model ${modelId}.`);
  }
  return { model, relation };
}

function ensureMetadata(record: { metadata?: Record<string, unknown> }): Record<string, unknown> {
  if (!record.metadata) {
    record.metadata = {};
  }
  return record.metadata;
}

function appendUnique(values: string[], value: string): string[] {
  return values.includes(value) ? values : [...values, value];
}

function removeValue(values: string[], value: string): string[] {
  return values.filter((entry) => entry !== value);
}

function requireStringUpdate(operation: PatchOperation, field: string, opName: string): string {
  const value = operation.updates?.[field];
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${opName} requires updates.${field}.`);
  }
  return value.trim();
}

type MetadataTarget =
  | { kind: "model"; model: ReturnType<typeof requireModel> }
  | { kind: "element"; model: ReturnType<typeof requireModel>; element: UmlElement }
  | { kind: "relation"; model: ReturnType<typeof requireModel>; relation: UmlRelation }
  | { kind: "diagram"; diagram: ReturnType<typeof requireDiagram> };

function resolveMetadataTarget(state: WorkspaceState, operation: PatchOperation, opName: string): MetadataTarget {
  const elementId = operation.elementId;
  const relationId = operation.relationId;
  const diagramId = operation.diagramId;
  const modelId = operation.modelId;

  if (elementId) {
    if (modelId) {
      const resolved = requireElement(state, modelId, elementId);
      return { kind: "element", ...resolved };
    }
    const resolved = findElement(state, elementId);
    if (!resolved) {
      throw new Error(`${opName} target element ${elementId} was not found.`);
    }
    return { kind: "element", model: resolved.model, element: resolved.element };
  }

  if (relationId) {
    if (modelId) {
      const resolved = requireRelation(state, modelId, relationId);
      return { kind: "relation", ...resolved };
    }
    const resolved = findRelation(state, relationId);
    if (!resolved) {
      throw new Error(`${opName} target relation ${relationId} was not found.`);
    }
    return { kind: "relation", model: resolved.model, relation: resolved.relation };
  }

  if (diagramId) {
    return { kind: "diagram", diagram: requireDiagram(state, diagramId) };
  }

  if (modelId) {
    return { kind: "model", model: requireModel(state, modelId) };
  }

  throw new Error(`${opName} requires modelId, diagramId, elementId, or relationId.`);
}

function metadataRecord(target: MetadataTarget): Record<string, unknown> {
  switch (target.kind) {
    case "model":
      return ensureMetadata(target.model.data);
    case "element":
      return ensureMetadata(target.element);
    case "relation":
      return ensureMetadata(target.relation);
    case "diagram":
      return ensureMetadata(target.diagram.data);
  }
}

function tagList(target: MetadataTarget): string[] {
  switch (target.kind) {
    case "element":
      target.element.tags = target.element.tags ?? [];
      return target.element.tags;
    case "relation":
      target.relation.tags = target.relation.tags ?? [];
      return target.relation.tags;
    case "model":
    case "diagram": {
      const metadata = metadataRecord(target);
      const tags = metadata.tags;
      metadata.tags = Array.isArray(tags) ? tags.filter((tag): tag is string => typeof tag === "string") : [];
      return metadata.tags as string[];
    }
  }
}

function ensureDiagramModelRef(state: WorkspaceState, diagramId: string, modelId: string): void {
  const diagram = requireDiagram(state, diagramId);
  if (!diagram.data.modelRefs.includes(modelId)) {
    diagram.data.modelRefs.push(modelId);
  }
}

function opRenameElement(state: WorkspaceState, operation: PatchOperation): void {
  const modelId = operation.modelId;
  const elementId = operation.elementId;
  if (!modelId || !elementId) {
    throw new Error("rename_element requires modelId and elementId.");
  }

  const name =
    (typeof operation.updates?.name === "string" && operation.updates.name.trim()) ||
    (typeof operation.element?.name === "string" && operation.element.name.trim());
  if (!name) {
    throw new Error("rename_element requires updates.name or element.name.");
  }

  const { element } = requireElement(state, modelId, elementId);
  element.name = name;
}

function opMoveElementToModel(state: WorkspaceState, operation: PatchOperation): void {
  const sourceModelId = operation.modelId;
  const elementId = operation.elementId;
  const targetModelId = operation.updates?.targetModelId;
  if (!sourceModelId || !elementId) {
    throw new Error("move_element_to_model requires modelId and elementId.");
  }
  if (typeof targetModelId !== "string" || !targetModelId.trim()) {
    throw new Error("move_element_to_model requires updates.targetModelId.");
  }
  if (sourceModelId === targetModelId) {
    throw new Error("move_element_to_model requires a different targetModelId.");
  }

  const sourceModel = requireModel(state, sourceModelId);
  const targetModel = requireModel(state, targetModelId);
  const normalized = endpointId(elementId);
  const index = sourceModel.data.elements.findIndex((candidate) => candidate.id === normalized);
  if (index < 0) {
    throw new Error(`Element ${elementId} was not found in model ${sourceModelId}.`);
  }
  if (targetModel.data.elements.some((candidate) => candidate.id === normalized)) {
    throw new Error(`Element ${normalized} already exists in model ${targetModelId}.`);
  }

  const element = sourceModel.data.elements[index];
  if (!element) {
    throw new Error(`Element ${elementId} was not found in model ${sourceModelId}.`);
  }
  sourceModel.data.elements.splice(index, 1);
  targetModel.data.elements.push(element);

  const movedRelations = sourceModel.data.relations.filter(
    (relation) => endpointId(relation.from) === normalized || endpointId(relation.to) === normalized
  );
  if (movedRelations.length > 0) {
    sourceModel.data.relations = sourceModel.data.relations.filter((relation) => !movedRelations.includes(relation));
    targetModel.data.relations.push(...movedRelations);
  }

  for (const diagram of state.diagrams) {
    if (!diagram.data.elementRefs.includes(normalized)) {
      continue;
    }
    ensureDiagramModelRef(state, diagram.data.id, targetModelId);
  }
}

function opSetEdgeRoute(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  const relationId = operation.relationId;
  if (!diagramId || !relationId) {
    throw new Error("set_edge_route requires diagramId and relationId.");
  }

  requireDiagram(state, diagramId);
  if (!findRelation(state, relationId)) {
    throw new Error(`Relation ${relationId} was not found.`);
  }

  const layout = requireLayout(state, diagramId);
  const current = layout.data.edges[relationId] ?? {};
  layout.data.edges[relationId] = {
    ...current,
    ...operation.updates
  };
}

function opApplyLayout(state: WorkspaceState, operation: PatchOperation): void {
  const diagramId = operation.diagramId;
  if (!diagramId) {
    throw new Error("apply_layout requires diagramId.");
  }

  requireDiagram(state, diagramId);
  const layout = requireLayout(state, diagramId);
  const nodes = operation.updates?.nodes;
  const edges = operation.updates?.edges;

  if (!nodes && !edges) {
    throw new Error("apply_layout requires updates.nodes and/or updates.edges.");
  }

  if (nodes && typeof nodes === "object" && !Array.isArray(nodes)) {
    layout.data.nodes = {
      ...layout.data.nodes,
      ...(nodes as Record<string, NodeLayout>)
    };
  }

  if (edges && typeof edges === "object" && !Array.isArray(edges)) {
    layout.data.edges = {
      ...layout.data.edges,
      ...(edges as Record<string, Record<string, unknown>>)
    };
  }
}

function opAddNote(state: WorkspaceState, operation: PatchOperation): void {
  const note = requireStringUpdate(operation, "note", "add_note");
  const target = resolveMetadataTarget(state, operation, "add_note");
  const metadata = metadataRecord(target);
  const notes = metadata.notes;
  metadata.notes = Array.isArray(notes) ? notes.filter((entry): entry is string => typeof entry === "string") : [];
  (metadata.notes as string[]).push(note);
}

function opAddTag(state: WorkspaceState, operation: PatchOperation): void {
  const tag = requireStringUpdate(operation, "tag", "add_tag");
  const target = resolveMetadataTarget(state, operation, "add_tag");
  const tags = tagList(target);
  if (!tags.includes(tag)) {
    tags.push(tag);
  }
}

function opRemoveTag(state: WorkspaceState, operation: PatchOperation): void {
  const tag = requireStringUpdate(operation, "tag", "remove_tag");
  const target = resolveMetadataTarget(state, operation, "remove_tag");
  const tags = tagList(target);
  const nextTags = removeValue(tags, tag);
  if (target.kind === "element") {
    target.element.tags = nextTags;
  } else if (target.kind === "relation") {
    target.relation.tags = nextTags;
  } else {
    metadataRecord(target).tags = nextTags;
  }
}

function opLinkDecision(state: WorkspaceState, operation: PatchOperation): void {
  const decisionId =
    (typeof operation.updates?.decisionId === "string" && operation.updates.decisionId.trim()) ||
    (typeof operation.updates?.reference === "string" && operation.updates.reference.trim());
  if (!decisionId) {
    throw new Error("link_decision requires updates.decisionId or updates.reference.");
  }

  const target = resolveMetadataTarget(state, operation, "link_decision");
  const metadata = metadataRecord(target);
  const linkedDecisions = metadata.linkedDecisions;
  metadata.linkedDecisions = Array.isArray(linkedDecisions)
    ? linkedDecisions.filter((entry): entry is string => typeof entry === "string")
    : [];
  metadata.linkedDecisions = appendUnique(metadata.linkedDecisions as string[], decisionId);
}

function opLinkPractice(state: WorkspaceState, operation: PatchOperation): void {
  const practiceId =
    (typeof operation.updates?.practiceId === "string" && operation.updates.practiceId.trim()) ||
    (typeof operation.updates?.reference === "string" && operation.updates.reference.trim());
  if (!practiceId) {
    throw new Error("link_practice requires updates.practiceId or updates.reference.");
  }

  const target = resolveMetadataTarget(state, operation, "link_practice");
  const metadata = metadataRecord(target);
  const linkedPractices = metadata.linkedPractices;
  metadata.linkedPractices = Array.isArray(linkedPractices)
    ? linkedPractices.filter((entry): entry is string => typeof entry === "string")
    : [];
  metadata.linkedPractices = appendUnique(metadata.linkedPractices as string[], practiceId);
}

function opSetStatus(state: WorkspaceState, operation: PatchOperation): void {
  const status = requireStringUpdate(operation, "status", "set_status");
  const target = resolveMetadataTarget(state, operation, "set_status");
  metadataRecord(target).status = status;
}

export function operationDiagnostics(errors: OperationError[]): Diagnostic[] {
  return errors.map((error) => ({
    level: "error" as const,
    code: "patch.operation_failed",
    message: `${error.op}: ${error.message}`,
    category: "patch"
  }));
}
