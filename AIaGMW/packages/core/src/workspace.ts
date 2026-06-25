import { mkdir, readFile, readdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import type {
  DiagramDetail,
  Diagnostic,
  DiagramSummary,
  DiagramType,
  ElementKind,
  ModelSummary,
  ModelType,
  NodeLayout,
  PatchProposal,
  ProposalSummary,
  RelationKind,
  UmlDiagram,
  UmlElement,
  UmlLayout,
  UmlModel,
  UmlRelation,
  WorkspaceIndex,
  WorkspaceInfoResponse,
  WorkspaceManifest
} from "@aiagmw/shared";
import { SchemaValidator } from "./schemaValidation";
import { applyOperations } from "./operations/executor";
import { validateLoadedWorkspace, buildWorkspaceIndex } from "./workspaceIndex";
import { loadArchitectureRules } from "./validation/rulesLoader";
import { detectArchitectureDiagnostics } from "./validation/architectureRules";
import { autoLayout as computeAutoLayout } from "./layout/autoLayout";
import { endpointId, findElement, findRelation } from "./workspaceHelpers";
import { relativePath, safeJoin, sanitizeFileName } from "./workspacePaths";

interface Loaded<T> {
  data: T;
  file: string;
  relativePath: string;
}

export interface WorkspaceState {
  root: string;
  manifest: WorkspaceManifest | null;
  models: Array<Loaded<UmlModel>>;
  diagrams: Array<Loaded<UmlDiagram>>;
  layouts: Array<Loaded<UmlLayout>>;
  proposals: Array<Loaded<PatchProposal>>;
  diagnostics: Diagnostic[];
  index: WorkspaceIndex;
}

export interface LoadWorkspaceOptions {
  root: string;
  schemaDir: string;
}

const emptyIndex: WorkspaceIndex = {
  models: [],
  diagrams: [],
  proposals: [],
  elementToModel: {},
  elementToDiagrams: {},
  relationToModel: {},
  tags: {}
};

export async function loadWorkspace(options: LoadWorkspaceOptions): Promise<WorkspaceState> {
  const root = path.resolve(options.root);
  const validator = await SchemaValidator.create(options.schemaDir);
  const diagnostics: Diagnostic[] = [];
  const workspaceFile = safeJoin(root, ".umlworkspace", "workspace.json");
  const manifestRead = await readJson<WorkspaceManifest>(workspaceFile);

  if (manifestRead.diagnostic) {
    diagnostics.push(manifestRead.diagnostic);
  }

  const manifest = manifestRead.value ?? null;
  if (manifest) {
    diagnostics.push(...validator.validate("workspace", manifest, relativePath(root, workspaceFile)));
  }

  const paths = manifest?.paths ?? {
    models: "models",
    diagrams: "diagrams",
    layouts: "layouts",
    proposals: "proposals",
    history: "history"
  };

  const models = await loadJsonDirectory<UmlModel>({
    root,
    dir: paths.models,
    pattern: ".umlmodel.json",
    kind: "model",
    validator,
    diagnostics
  });
  const diagrams = await loadJsonDirectory<UmlDiagram>({
    root,
    dir: paths.diagrams,
    pattern: ".diagram.json",
    kind: "diagram",
    validator,
    diagnostics
  });
  const layouts = await loadJsonDirectory<UmlLayout>({
    root,
    dir: paths.layouts,
    pattern: ".layout.json",
    kind: "layout",
    validator,
    diagnostics
  });
  const proposals = await loadProposals({
    root,
    dir: paths.proposals,
    validator,
    diagnostics
  });

  diagnostics.push(...validateLoadedWorkspace(models, diagrams, layouts));
  const architectureRules = await loadArchitectureRules(root);
  diagnostics.push(...detectArchitectureDiagnostics(models, architectureRules));
  const index = buildWorkspaceIndex(models, diagrams, proposals);

  return {
    root,
    manifest,
    models,
    diagrams,
    layouts,
    proposals,
    diagnostics,
    index
  };
}

export function toWorkspaceInfo(state: WorkspaceState): WorkspaceInfoResponse {
  return {
    workspace: state.manifest,
    index: state.index,
    diagnostics: state.diagnostics,
    root: state.root
  };
}

export function getDiagramDetail(state: WorkspaceState, diagramId: string): DiagramDetail | null {
  const diagram = state.diagrams.find((entry) => entry.data.id === diagramId);
  if (!diagram) {
    return null;
  }

  const models = state.models.filter((entry) => diagram.data.modelRefs.includes(entry.data.id));
  const modelData = models.map((entry) => entry.data);
  const elements = diagram.data.elementRefs.flatMap((elementId) => {
    const resolved = findElement(state, elementId);
    return resolved ? [{ ...resolved.element, modelId: resolved.model.data.id }] : [];
  });
  const relations = diagram.data.relationRefs.flatMap((relationId) => {
    const resolved = findRelation(state, relationId);
    return resolved ? [{ ...resolved.relation, modelId: resolved.model.data.id }] : [];
  });
  const layout = state.layouts.find((entry) => entry.data.diagramId === diagramId)?.data ?? {
    schema: "umllayout.v1",
    diagramId,
    nodes: {},
    edges: {}
  };

  return {
    diagram: diagram.data,
    layout,
    models: modelData,
    elements,
    relations,
    diagnostics: state.diagnostics.filter((diagnostic) => diagnostic.targetId === diagramId)
  };
}

export async function createElementInDiagram(
  options: LoadWorkspaceOptions,
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
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const modelId = input.modelId ?? diagram.data.modelRefs[0];

  if (!modelId) {
    throw new Error(`Diagram ${diagramId} is not linked to a model.`);
  }

  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const element: UmlElement = {
    id: makeUniqueElementId(model.data, input.kind, input.name),
    kind: input.kind,
    name: input.name,
    responsibilities: [],
    properties: [],
    methods: [],
    constraints: [],
    tags: [],
    metadata: {
      origin: "manual"
    }
  };

  model.data.elements.push(element);
  if (!diagram.data.elementRefs.includes(element.id)) {
    diagram.data.elementRefs.push(element.id);
  }

  const layout = await ensureLayout(state, diagram.data.id);
  layout.data.nodes[element.id] = {
    x: input.x ?? 120,
    y: input.y ?? 120,
    width: input.width ?? 260,
    height: input.height ?? 150
  };

  await writeJson(model.file, model.data);
  await writeJson(diagram.file, diagram.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after element creation.`);
  }
  return detail;
}

export async function addElementToDiagram(
  options: LoadWorkspaceOptions,
  diagramId: string,
  input: {
    elementId: string;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
  }
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const resolved = findElement(state, input.elementId);
  if (!resolved) {
    throw new Error(`Element ${input.elementId} was not found.`);
  }
  if (!diagram.data.modelRefs.includes(resolved.model.data.id)) {
    throw new Error(
      `Element ${input.elementId} belongs to model ${resolved.model.data.id}, which is not linked to diagram ${diagramId}.`
    );
  }

  if (!diagram.data.elementRefs.includes(resolved.element.id)) {
    diagram.data.elementRefs.push(resolved.element.id);
  }

  const layout = await ensureLayout(state, diagram.data.id);
  layout.data.nodes[resolved.element.id] = {
    ...layout.data.nodes[resolved.element.id],
    x: input.x ?? layout.data.nodes[resolved.element.id]?.x ?? 120,
    y: input.y ?? layout.data.nodes[resolved.element.id]?.y ?? 120,
    width: input.width ?? layout.data.nodes[resolved.element.id]?.width ?? 260,
    height: input.height ?? layout.data.nodes[resolved.element.id]?.height ?? 150
  };

  await writeJson(diagram.file, diagram.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after element membership update.`);
  }
  return detail;
}

export async function createRelationInDiagram(
  options: LoadWorkspaceOptions,
  diagramId: string,
  input: {
    kind: RelationKind;
    from: string;
    to: string;
    name?: string;
    modelId?: string;
  }
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const from = endpointId(input.from);
  const to = endpointId(input.to);
  const fromElement = findElement(state, from);
  const toElement = findElement(state, to);

  if (!fromElement) {
    throw new Error(`Relation source ${input.from} was not found.`);
  }
  if (!toElement) {
    throw new Error(`Relation target ${input.to} was not found.`);
  }

  const modelId = input.modelId ?? fromElement.model.data.id ?? diagram.data.modelRefs[0];
  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const relation: UmlRelation = {
    id: makeUniqueRelationId(model.data, input.kind, from, to),
    kind: input.kind,
    from,
    to,
    name: input.name?.trim() || relationLabel(input.kind),
    stereotypes: [],
    tags: [],
    metadata: {
      origin: "manual"
    }
  };

  model.data.relations.push(relation);
  if (!diagram.data.relationRefs.includes(relation.id)) {
    diagram.data.relationRefs.push(relation.id);
  }
  for (const elementId of [from, to]) {
    if (!diagram.data.elementRefs.includes(elementId)) {
      diagram.data.elementRefs.push(elementId);
    }
  }

  await writeJson(model.file, model.data);
  await writeJson(diagram.file, diagram.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after relation creation.`);
  }
  return detail;
}

export async function addRelationToDiagram(
  options: LoadWorkspaceOptions,
  diagramId: string,
  input: {
    relationId: string;
    x?: number;
    y?: number;
    width?: number;
    height?: number;
  }
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const resolved = findRelation(state, input.relationId);
  if (!resolved) {
    throw new Error(`Relation ${input.relationId} was not found.`);
  }
  if (!diagram.data.modelRefs.includes(resolved.model.data.id)) {
    throw new Error(
      `Relation ${input.relationId} belongs to model ${resolved.model.data.id}, which is not linked to diagram ${diagramId}.`
    );
  }

  const from = endpointId(resolved.relation.from);
  const to = endpointId(resolved.relation.to);
  const fromElement = findElement(state, from);
  const toElement = findElement(state, to);
  if (!fromElement) {
    throw new Error(`Relation source ${from} was not found.`);
  }
  if (!toElement) {
    throw new Error(`Relation target ${to} was not found.`);
  }
  for (const endpoint of [fromElement, toElement]) {
    if (!diagram.data.modelRefs.includes(endpoint.model.data.id)) {
      throw new Error(`Relation ${input.relationId} references element ${endpoint.element.id} from an unlinked model.`);
    }
  }

  const layout = await ensureLayout(state, diagram.data.id);
  const baseX = input.x ?? 160 + diagram.data.elementRefs.length * 32;
  const baseY = input.y ?? 160 + diagram.data.elementRefs.length * 24;
  for (const [index, elementId] of [from, to].entries()) {
    if (!diagram.data.elementRefs.includes(elementId)) {
      diagram.data.elementRefs.push(elementId);
    }
    layout.data.nodes[elementId] = {
      ...layout.data.nodes[elementId],
      x: layout.data.nodes[elementId]?.x ?? baseX + index * 320,
      y: layout.data.nodes[elementId]?.y ?? baseY,
      width: input.width ?? layout.data.nodes[elementId]?.width ?? 260,
      height: input.height ?? layout.data.nodes[elementId]?.height ?? 150
    };
  }

  if (!diagram.data.relationRefs.includes(resolved.relation.id)) {
    diagram.data.relationRefs.push(resolved.relation.id);
  }

  await writeJson(diagram.file, diagram.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after relation membership update.`);
  }
  return detail;
}

export async function createDiagram(
  options: LoadWorkspaceOptions,
  input: {
    name: string;
    diagramType: DiagramType;
    modelRefs?: string[];
  }
): Promise<UmlDiagram> {
  const state = await loadWorkspace(options);
  const modelRefs = input.modelRefs?.length ? input.modelRefs : state.models[0] ? [state.models[0].data.id] : [];
  if (modelRefs.length === 0) {
    throw new Error("A diagram needs at least one model reference.");
  }

  for (const modelRef of modelRefs) {
    if (!state.models.some((entry) => entry.data.id === modelRef)) {
      throw new Error(`Model ${modelRef} was not found.`);
    }
  }

  const diagram: UmlDiagram = {
    schema: "umldiagram.v1",
    id: makeUniqueDiagramId(
      state.diagrams.map((entry) => entry.data.id),
      input.name,
      input.diagramType
    ),
    name: input.name,
    diagramType: input.diagramType,
    modelRefs,
    elementRefs: [],
    relationRefs: [],
    metadata: {
      origin: "manual",
      status: "draft",
      tags: []
    }
  };
  const layout: UmlLayout = {
    schema: "umllayout.v1",
    diagramId: diagram.id,
    nodes: {},
    edges: {}
  };

  const diagramsDir = state.manifest?.paths.diagrams ?? "diagrams";
  const layoutsDir = state.manifest?.paths.layouts ?? "layouts";
  await writeJson(safeJoin(state.root, diagramsDir, `${sanitizeFileName(diagram.id)}.diagram.json`), diagram);
  await writeJson(safeJoin(state.root, layoutsDir, `${sanitizeFileName(diagram.id)}.layout.json`), layout);

  return diagram;
}

export async function createModel(
  options: LoadWorkspaceOptions,
  input: {
    name: string;
    modelType: ModelType;
  }
): Promise<UmlModel> {
  const state = await loadWorkspace(options);
  const model: UmlModel = {
    schema: "umlmodel.v1",
    id: makeUniqueModelId(
      state.models.map((entry) => entry.data.id),
      input.name
    ),
    name: input.name,
    modelType: input.modelType,
    elements: [],
    relations: [],
    metadata: {
      origin: "manual",
      status: "draft",
      tags: []
    }
  };

  const modelsDir = state.manifest?.paths.models ?? "models";
  await writeJson(safeJoin(state.root, modelsDir, `${sanitizeFileName(model.id)}.umlmodel.json`), model);
  return model;
}

export async function updateElement(
  options: LoadWorkspaceOptions,
  modelId: string,
  elementId: string,
  updates: Partial<UmlElement>
): Promise<UmlElement> {
  const state = await loadWorkspace(options);
  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const element = model.data.elements.find((candidate) => candidate.id === elementId);

  if (!element) {
    throw new Error(`Element ${elementId} was not found in model ${modelId}.`);
  }

  Object.assign(element, {
    ...updates,
    id: element.id,
    metadata: {
      ...(element.metadata ?? {}),
      ...(updates.metadata ?? {}),
      updatedAt: new Date().toISOString()
    }
  });

  await writeJson(model.file, model.data);
  return element;
}

export async function updateRelation(
  options: LoadWorkspaceOptions,
  modelId: string,
  relationId: string,
  updates: Partial<UmlRelation>
): Promise<UmlRelation> {
  const state = await loadWorkspace(options);
  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const relation = model.data.relations.find((candidate) => candidate.id === relationId);

  if (!relation) {
    throw new Error(`Relation ${relationId} was not found in model ${modelId}.`);
  }

  const nextFrom = updates.from ? endpointId(updates.from) : relation.from;
  const nextTo = updates.to ? endpointId(updates.to) : relation.to;
  if (!findElement(state, nextFrom)) {
    throw new Error(`Relation source ${nextFrom} was not found.`);
  }
  if (!findElement(state, nextTo)) {
    throw new Error(`Relation target ${nextTo} was not found.`);
  }

  Object.assign(relation, {
    ...updates,
    id: relation.id,
    from: nextFrom,
    to: nextTo,
    metadata: {
      ...(relation.metadata ?? {}),
      ...(updates.metadata ?? {}),
      updatedAt: new Date().toISOString()
    }
  });

  await writeJson(model.file, model.data);
  return relation;
}

export async function removeElementFromDiagram(
  options: LoadWorkspaceOptions,
  diagramId: string,
  elementId: string
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const layout = await ensureLayout(state, diagramId);

  diagram.data.elementRefs = diagram.data.elementRefs.filter((id) => id !== elementId);
  const visibleElements = new Set(diagram.data.elementRefs);
  const removedRelationIds: string[] = [];
  diagram.data.relationRefs = diagram.data.relationRefs.filter((relationId) => {
    const relation = findRelation(state, relationId)?.relation;
    const keep = relation ? visibleElements.has(endpointId(relation.from)) && visibleElements.has(endpointId(relation.to)) : false;
    if (!keep) {
      removedRelationIds.push(relationId);
    }
    return keep;
  });
  delete layout.data.nodes[elementId];
  for (const relationId of removedRelationIds) {
    delete layout.data.edges[relationId];
  }

  await writeJson(diagram.file, diagram.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after element removal.`);
  }
  return detail;
}

export async function deleteElementFromModel(
  options: LoadWorkspaceOptions,
  modelId: string,
  elementId: string
): Promise<void> {
  const state = await loadWorkspace(options);
  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const existing = model.data.elements.find((element) => element.id === elementId);
  if (!existing) {
    throw new Error(`Element ${elementId} was not found in model ${modelId}.`);
  }

  const removedRelationIds = new Set(
    model.data.relations
      .filter((relation) => endpointId(relation.from) === elementId || endpointId(relation.to) === elementId)
      .map((relation) => relation.id)
  );
  model.data.elements = model.data.elements.filter((element) => element.id !== elementId);
  model.data.relations = model.data.relations.filter((relation) => !removedRelationIds.has(relation.id));

  const touchedDiagrams = state.diagrams.filter(
    (diagram) => diagram.data.elementRefs.includes(elementId) || diagram.data.relationRefs.some((id) => removedRelationIds.has(id))
  );
  const touchedLayouts = state.layouts.filter(
    (layout) => layout.data.nodes[elementId] || [...removedRelationIds].some((id) => layout.data.edges[id])
  );

  for (const diagram of touchedDiagrams) {
    diagram.data.elementRefs = diagram.data.elementRefs.filter((id) => id !== elementId);
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => !removedRelationIds.has(id));
    await writeJson(diagram.file, diagram.data);
  }

  for (const layout of touchedLayouts) {
    delete layout.data.nodes[elementId];
    for (const relationId of removedRelationIds) {
      delete layout.data.edges[relationId];
    }
    await writeJson(layout.file, layout.data);
  }

  await writeJson(model.file, model.data);
}

export async function removeRelationFromDiagram(
  options: LoadWorkspaceOptions,
  diagramId: string,
  relationId: string
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const layout = await ensureLayout(state, diagramId);

  diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => id !== relationId);
  delete layout.data.edges[relationId];

  await writeJson(diagram.file, diagram.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after relation removal.`);
  }
  return detail;
}

export async function deleteRelationFromModel(
  options: LoadWorkspaceOptions,
  modelId: string,
  relationId: string
): Promise<void> {
  const state = await loadWorkspace(options);
  const model = requireLoaded(state.models.find((entry) => entry.data.id === modelId), "model", modelId);
  const existing = model.data.relations.find((relation) => relation.id === relationId);
  if (!existing) {
    throw new Error(`Relation ${relationId} was not found in model ${modelId}.`);
  }

  model.data.relations = model.data.relations.filter((relation) => relation.id !== relationId);

  const touchedDiagrams = state.diagrams.filter((diagram) => diagram.data.relationRefs.includes(relationId));
  const touchedLayouts = state.layouts.filter((layout) => layout.data.edges[relationId]);

  for (const diagram of touchedDiagrams) {
    diagram.data.relationRefs = diagram.data.relationRefs.filter((id) => id !== relationId);
    await writeJson(diagram.file, diagram.data);
  }

  for (const layout of touchedLayouts) {
    delete layout.data.edges[relationId];
    await writeJson(layout.file, layout.data);
  }

  await writeJson(model.file, model.data);
}

export async function updateNodeLayout(
  options: LoadWorkspaceOptions,
  diagramId: string,
  elementId: string,
  updates: Partial<NodeLayout>
): Promise<UmlLayout> {
  const state = await loadWorkspace(options);
  const layout = await ensureLayout(state, diagramId);
  const op =
    updates.width !== undefined || updates.height !== undefined
      ? { op: "set_node_size" as const, diagramId, elementId, updates }
      : { op: "set_node_position" as const, diagramId, elementId, updates };
  const batch = applyOperations(state, [op]);
  if (batch.errors.length > 0) {
    throw new Error(batch.errors.map((entry) => entry.message).join("; "));
  }
  await writeJson(layout.file, layout.data);
  return layout.data;
}

export async function applyAutoLayout(
  options: LoadWorkspaceOptions,
  diagramId: string
): Promise<DiagramDetail> {
  const state = await loadWorkspace(options);
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const layout = await ensureLayout(state, diagramId);
  layout.data = computeAutoLayout(diagram.data.elementRefs, layout.data);
  await writeJson(layout.file, layout.data);

  const next = await loadWorkspace(options);
  const detail = getDiagramDetail(next, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} disappeared after auto layout.`);
  }
  return detail;
}

export async function submitProposal(
  options: LoadWorkspaceOptions,
  proposal: PatchProposal
): Promise<ProposalSummary> {
  const validator = await SchemaValidator.create(options.schemaDir);
  const diagnostics = validator.validate("patch", proposal);
  if (diagnostics.some((diagnostic) => diagnostic.level === "error")) {
    throw new Error(`Patch proposal is invalid: ${diagnostics.map((diagnostic) => diagnostic.message).join("; ")}`);
  }

  const root = path.resolve(options.root);
  const id = sanitizeFileName(proposal.id);
  const file = safeJoin(root, "proposals", "pending", `${id}.patch.json`);
  await mkdir(path.dirname(file), { recursive: true });
  await writeJson(file, {
    ...proposal,
    status: "pending"
  });

  return {
    id: proposal.id,
    title: proposal.title,
    status: "pending",
    risk: proposal.risk,
    path: relativePath(root, file),
    operationCount: proposal.operations.length
  };
}

export function searchModel(state: WorkspaceState, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [];
  }

  const results: Array<Record<string, unknown>> = [];
  for (const model of state.models) {
    for (const element of model.data.elements) {
      const haystack = [
        element.id,
        element.name,
        element.kind,
        ...(element.tags ?? []),
        ...(element.stereotypes ?? []),
        ...(element.responsibilities ?? [])
      ]
        .join(" ")
        .toLowerCase();

      if (haystack.includes(normalized)) {
        results.push({
          type: "element",
          id: element.id,
          modelId: model.data.id,
          name: element.name,
          kind: element.kind,
          diagrams: state.index.elementToDiagrams[element.id] ?? []
        });
      }
    }

    for (const relation of model.data.relations) {
      const haystack = [relation.id, relation.name, relation.kind, relation.from, relation.to, ...(relation.tags ?? [])]
        .join(" ")
        .toLowerCase();

      if (haystack.includes(normalized)) {
        results.push({
          type: "relation",
          id: relation.id,
          modelId: model.data.id,
          name: relation.name,
          kind: relation.kind,
          from: relation.from,
          to: relation.to
        });
      }
    }
  }
  return results;
}

export function getElementContext(state: WorkspaceState, elementId: string) {
  const resolved = findElement(state, elementId);
  if (!resolved) {
    return null;
  }

  const relations = resolved.model.data.relations.filter(
    (relation) => endpointId(relation.from) === elementId || endpointId(relation.to) === elementId
  );

  return {
    element: resolved.element,
    modelId: resolved.model.data.id,
    relations,
    diagrams: state.index.elementToDiagrams[elementId] ?? [],
    diagnostics: state.diagnostics.filter((diagnostic) => diagnostic.targetId === elementId)
  };
}

export async function moveProposal(
  options: LoadWorkspaceOptions,
  proposalId: string,
  status: "accepted" | "rejected" | "archived"
): Promise<ProposalSummary> {
  const state = await loadWorkspace(options);
  const proposal = requireLoaded(state.proposals.find((entry) => entry.data.id === proposalId), "proposal", proposalId);
  const root = path.resolve(options.root);
  const targetFile = safeJoin(root, "proposals", status, path.basename(proposal.file));
  await mkdir(path.dirname(targetFile), { recursive: true });
  proposal.data.status = status;
  await writeJson(proposal.file, proposal.data);
  await rename(proposal.file, targetFile);
  return {
    id: proposal.data.id,
    title: proposal.data.title,
    status,
    risk: proposal.data.risk,
    path: relativePath(root, targetFile),
    operationCount: proposal.data.operations.length
  };
}

async function loadJsonDirectory<T>(options: {
  root: string;
  dir: string;
  pattern: string;
  kind: "model" | "diagram" | "layout";
  validator: SchemaValidator;
  diagnostics: Diagnostic[];
}): Promise<Array<Loaded<T>>> {
  const dirPath = safeJoin(options.root, options.dir);
  const files = await listFiles(dirPath, options.pattern);
  const loaded: Array<Loaded<T>> = [];

  for (const file of files) {
    const read = await readJson<T>(file);
    if (read.diagnostic) {
      options.diagnostics.push(read.diagnostic);
      continue;
    }
    if (!read.value) {
      continue;
    }

    const fileRelativePath = relativePath(options.root, file);
    options.diagnostics.push(...options.validator.validate(options.kind, read.value, fileRelativePath));
    loaded.push({ data: read.value, file, relativePath: fileRelativePath });
  }

  return loaded;
}

async function loadProposals(options: {
  root: string;
  dir: string;
  validator: SchemaValidator;
  diagnostics: Diagnostic[];
}): Promise<Array<Loaded<PatchProposal>>> {
  const dirPath = safeJoin(options.root, options.dir);
  const files = await listFiles(dirPath, ".patch.json");
  const loaded: Array<Loaded<PatchProposal>> = [];

  for (const file of files) {
    const read = await readJson<PatchProposal>(file);
    if (read.diagnostic) {
      options.diagnostics.push(read.diagnostic);
      continue;
    }
    if (!read.value) {
      continue;
    }

    const fileRelativePath = relativePath(options.root, file);
    options.diagnostics.push(...options.validator.validate("patch", read.value, fileRelativePath));
    loaded.push({ data: read.value, file, relativePath: fileRelativePath });
  }

  return loaded;
}

async function listFiles(dirPath: string, suffix: string): Promise<string[]> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true });
    const nested = await Promise.all(
      entries.map(async (entry) => {
        const entryPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
          return listFiles(entryPath, suffix);
        }
        return entry.isFile() && entry.name.endsWith(suffix) ? [entryPath] : [];
      })
    );
    return nested.flat().sort();
  } catch {
    return [];
  }
}

async function readJson<T>(file: string): Promise<{ value?: T; diagnostic?: Diagnostic }> {
  try {
    const raw = await readFile(file, "utf8");
    return { value: JSON.parse(raw) as T };
  } catch (error) {
    return {
      diagnostic: {
        level: "error",
        code: "file.invalid_json",
        message: error instanceof Error ? error.message : `Could not read ${file}.`,
        file,
        category: "file"
      }
    };
  }
}

async function writeJson(file: string, value: unknown): Promise<void> {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function ensureLayout(state: WorkspaceState, diagramId: string): Promise<Loaded<UmlLayout>> {
  const existing = state.layouts.find((entry) => entry.data.diagramId === diagramId);
  if (existing) {
    return existing;
  }

  const manifest = state.manifest;
  const layoutsDir = manifest?.paths.layouts ?? "layouts";
  const diagram = requireLoaded(state.diagrams.find((entry) => entry.data.id === diagramId), "diagram", diagramId);
  const fileName = `${sanitizeFileName(diagram.data.id)}.layout.json`;
  const file = safeJoin(state.root, layoutsDir, fileName);
  const layout: UmlLayout = {
    schema: "umllayout.v1",
    diagramId,
    nodes: {},
    edges: {}
  };
  return {
    data: layout,
    file,
    relativePath: relativePath(state.root, file)
  };
}

function makeUniqueElementId(model: UmlModel, kind: ElementKind, name: string): string {
  const base = `${kind}.${toPascalIdentifier(name)}`;
  const existing = new Set(model.elements.map((element) => element.id));
  if (!existing.has(base)) {
    return base;
  }

  let index = 2;
  while (existing.has(`${base}${index}`)) {
    index += 1;
  }
  return `${base}${index}`;
}

function makeUniqueRelationId(model: UmlModel, kind: RelationKind, from: string, to: string): string {
  const cleanFrom = from.split(".").at(-1) ?? from;
  const cleanTo = to.split(".").at(-1) ?? to;
  const base = `relation.${cleanFrom}__${kind}__${cleanTo}`;
  const existing = new Set(model.relations.map((relation) => relation.id));
  if (!existing.has(base)) {
    return base;
  }

  let index = 2;
  while (existing.has(`${base}${index}`)) {
    index += 1;
  }
  return `${base}${index}`;
}

function makeUniqueDiagramId(existingIds: string[], name: string, diagramType: DiagramType): string {
  const base = `diagram.${toKebabIdentifier(name)}.${diagramType}`;
  const existing = new Set(existingIds);
  if (!existing.has(base)) {
    return base;
  }

  let index = 2;
  while (existing.has(`${base}${index}`)) {
    index += 1;
  }
  return `${base}${index}`;
}

function makeUniqueModelId(existingIds: string[], name: string): string {
  const base = `model.${toKebabIdentifier(name)}`;
  const existing = new Set(existingIds);
  if (!existing.has(base)) {
    return base;
  }

  let index = 2;
  while (existing.has(`${base}${index}`)) {
    index += 1;
  }
  return `${base}${index}`;
}

function toPascalIdentifier(value: string): string {
  const cleaned = value
    .replace(/[^a-zA-Z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join("");
  return cleaned || "Element";
}

function toKebabIdentifier(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "diagram"
  );
}

function requireLoaded<T>(value: Loaded<T> | undefined, label: string, id: string): Loaded<T> {
  if (!value) {
    throw new Error(`${label} ${id} was not found.`);
  }
  return value;
}

export function relationLabel(kind: RelationKind): string {
  return kind.replaceAll("_", " ");
}
