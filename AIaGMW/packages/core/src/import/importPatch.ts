import path from "node:path";
import type {
  DiagramType,
  ElementKind,
  ModelType,
  PatchOperation,
  PatchProposal,
  UmlDiagram,
  UmlElement,
  UmlLayout,
  UmlModel,
  UmlRelation
} from "@aiagmw/shared";
import { simulatePatch } from "../patch/simulatePatch";
import { runTransaction } from "../transaction";
import type { DiagramImportRequest } from "../importExport";
import { parseMermaid, parsePlantUml } from "../importExport";
import { loadWorkspace, type LoadWorkspaceOptions } from "../workspace";
import { relativePath, safeJoin, sanitizeFileName } from "../workspacePaths";

export interface ImportConflict {
  type: "element_name_kind" | "model_name" | "diagram_id" | "element_id";
  message: string;
  importedName?: string;
  importedKind?: string;
  existingId?: string;
}

export interface ImportPatchBuildResult {
  proposal: PatchProposal;
  conflicts: ImportConflict[];
  sourceRelativePath: string;
  modelId: string;
  diagramId: string;
  imported: {
    elements: number;
    relations: number;
  };
}

export interface ImportPatchApplyResult {
  model: UmlModel;
  diagram: UmlDiagram;
  layout: UmlLayout;
  sourcePath: string;
  proposal: PatchProposal;
  imported: {
    elements: number;
    relations: number;
  };
}

export async function buildImportPatch(
  options: LoadWorkspaceOptions,
  input: DiagramImportRequest
): Promise<ImportPatchBuildResult> {
  if (!input.source.trim()) {
    throw new Error("Import source is required.");
  }

  const state = await loadWorkspace(options);
  const parsed = input.format === "plantuml" ? parsePlantUml(input.source) : parseMermaid(input.source);
  const displayName = input.name?.trim() || parsed.name;
  const now = new Date().toISOString();
  const root = path.resolve(state.root);
  const importsDir = state.manifest?.paths.imports ?? "imports";
  const modelsDir = state.manifest?.paths.models ?? "models";
  const diagramsDir = state.manifest?.paths.diagrams ?? "diagrams";
  const layoutsDir = state.manifest?.paths.layouts ?? "layouts";
  const sourceExtension = input.format === "plantuml" ? "puml" : "mmd";
  const baseFileName = sanitizeFileName(toKebabIdentifier(displayName));
  const sourceRelativePath = path.join(importsDir, `${baseFileName}.${sourceExtension}`).replace(/\\/g, "/");

  const modelId = uniqueId(
    `model.${toKebabIdentifier(displayName)}`,
    state.models.map((entry) => entry.data.id)
  );
  const diagramId = uniqueId(
    `diagram.${toKebabIdentifier(displayName)}.${parsed.diagramType}`,
    state.diagrams.map((entry) => entry.data.id)
  );
  const proposalId = uniqueId(
    `proposal.import.${toKebabIdentifier(displayName)}`,
    state.proposals.map((entry) => entry.data.id)
  );

  const materialized = materializeImportEntities(parsed, {
    displayName,
    modelId,
    diagramId,
    format: input.format,
    sourceRelativePath,
    sourcePath: input.sourcePath,
    importedAt: now
  });

  const conflicts = detectImportConflicts(state, displayName, diagramId, materialized.elements);
  const conflictElementIds = new Set(
    conflicts.filter((conflict) => conflict.type === "element_name_kind" && conflict.existingId).map((conflict) => {
      const element = materialized.elements.find(
        (candidate) => candidate.name === conflict.importedName && candidate.kind === conflict.importedKind
      );
      return element?.id ?? "";
    }).filter(Boolean)
  );

  const elements = materialized.elements.filter((element) => !conflictElementIds.has(element.id));
  const elementIds = new Set(elements.map((element) => element.id));
  const relations = materialized.relations.filter(
    (relation) => elementIds.has(relation.from) && elementIds.has(relation.to)
  );

  const modelFile = safeJoin(root, modelsDir, `${sanitizeFileName(modelId)}.umlmodel.json`);
  const diagramFile = safeJoin(root, diagramsDir, `${sanitizeFileName(diagramId)}.diagram.json`);
  const layoutFile = safeJoin(root, layoutsDir, `${sanitizeFileName(diagramId)}.layout.json`);

  const model: UmlModel = {
    ...materialized.model,
    id: modelId,
    name: displayName,
    elements,
    relations
  };
  const diagram: UmlDiagram = {
    ...materialized.diagram,
    id: diagramId,
    name: `${displayName} Diagram`,
    modelRefs: [modelId],
    elementRefs: elements.map((element) => element.id),
    relationRefs: relations.map((relation) => relation.id)
  };
  const layout: UmlLayout = {
    ...materialized.layout,
    diagramId,
    nodes: Object.fromEntries(
      elements.map((element, index) => [element.id, layoutForIndex(index, element.kind)])
    )
  };

  const operations: PatchOperation[] = [
    {
      op: "create_model",
      updates: {
        model: {
          id: model.id,
          name: model.name,
          modelType: model.modelType,
          metadata: model.metadata
        },
        file: modelFile,
        relativePath: relativePath(root, modelFile)
      }
    },
    {
      op: "create_diagram",
      updates: {
        diagram: {
          id: diagram.id,
          name: diagram.name,
          diagramType: diagram.diagramType,
          modelRefs: diagram.modelRefs,
          metadata: diagram.metadata
        },
        file: diagramFile,
        relativePath: relativePath(root, diagramFile)
      }
    },
    ...elements.map(
      (element): PatchOperation => ({
        op: "add_element",
        modelId: model.id,
        element
      })
    ),
    ...relations.map(
      (relation): PatchOperation => ({
        op: "add_relation",
        modelId: model.id,
        relation
      })
    ),
    ...elements.map(
      (element): PatchOperation => ({
        op: "add_to_diagram",
        diagramId: diagram.id,
        elementId: element.id
      })
    ),
    ...relations.map(
      (relation): PatchOperation => ({
        op: "add_to_diagram",
        diagramId: diagram.id,
        relationId: relation.id
      })
    ),
    ...elements.map(
      (element): PatchOperation => ({
        op: "set_node_position",
        diagramId: diagram.id,
        elementId: element.id,
        updates: { ...(layout.nodes[element.id] ?? { x: 0, y: 0 }) }
      })
    ),
    {
      op: "apply_layout",
      diagramId: diagram.id,
      updates: { nodes: layout.nodes, edges: layout.edges }
    }
  ];

  const proposal: PatchProposal = {
    schema: "umlpatch.v1",
    id: proposalId,
    title: `Import ${displayName}`,
    intent: `Import ${input.format} diagram "${displayName}" into the workspace as a reviewable patch.`,
    status: "pending",
    risk: conflicts.length ? "medium" : "low",
    reasoningSummary: conflicts.length
      ? `Import parsed ${materialized.elements.length} elements with ${conflicts.length} conflict(s) skipped.`
      : `Import parsed ${elements.length} element(s) and ${relations.length} relation(s).`,
    operations,
    metadata: {
      origin: "import",
      importedFrom: input.format,
      sourcePath: sourceRelativePath,
      importedAt: now,
      originalSourcePath: input.sourcePath,
      conflicts,
      importTargets: {
        modelId,
        diagramId,
        modelFile: relativePath(root, modelFile),
        diagramFile: relativePath(root, diagramFile),
        layoutFile: relativePath(root, layoutFile)
      }
    }
  };

  return {
    proposal,
    conflicts,
    sourceRelativePath,
    modelId,
    diagramId,
    imported: {
      elements: elements.length,
      relations: relations.length
    }
  };
}

export async function applyImportPatchBuild(
  options: LoadWorkspaceOptions,
  built: ImportPatchBuildResult,
  sourceText: string
): Promise<ImportPatchApplyResult> {
  const state = await loadWorkspace(options);
  const simulation = simulatePatch(state, built.proposal);
  if (!simulation.applicable) {
    const messages = simulation.diagnostics.map((diagnostic) => diagnostic.message).join("; ");
    throw new Error(`Import patch is not applicable: ${messages}`);
  }

  const root = path.resolve(state.root);
  const sourceFile = safeJoin(root, built.sourceRelativePath);
  const writes = collectImportWrites(simulation.before, simulation.after, root, state);
  writes.push({ file: sourceFile, data: normalizedText(sourceText) });
  await runTransaction(writes);

  const model = simulation.after.models.find((entry) => entry.data.id === built.modelId)?.data;
  const diagram = simulation.after.diagrams.find((entry) => entry.data.id === built.diagramId)?.data;
  const layout = simulation.after.layouts.find((entry) => entry.data.diagramId === built.diagramId)?.data;

  if (!model || !diagram || !layout) {
    throw new Error("Import patch did not materialize expected model, diagram, or layout.");
  }

  return {
    model,
    diagram,
    layout,
    sourcePath: built.sourceRelativePath,
    proposal: built.proposal,
    imported: built.imported
  };
}

function materializeImportEntities(
  parsed: ReturnType<typeof parsePlantUml>,
  context: {
    displayName: string;
    modelId: string;
    diagramId: string;
    format: DiagramImportRequest["format"];
    sourceRelativePath: string;
    sourcePath?: string;
    importedAt: string;
  }
): {
  model: UmlModel;
  diagram: UmlDiagram;
  layout: UmlLayout;
  elements: UmlElement[];
  relations: UmlRelation[];
} {
  const elementIds = new Set<string>();
  const keyToElementId = new Map<string, string>();
  const elements = ensureImplicitElements(parsed).map((element) => {
    const id = uniqueId(`${element.kind}.${toPascalIdentifier(element.name)}`, [...elementIds]);
    elementIds.add(id);
    keyToElementId.set(element.key, id);
    return {
      id,
      kind: element.kind,
      name: element.name,
      stereotypes: [],
      responsibilities: [],
      properties: [],
      methods: [],
      constraints: [],
      tags: ["imported"],
      metadata: {
        ...(element.metadata ?? {}),
        origin: "import",
        importedFrom: context.format,
        sourcePath: context.sourceRelativePath,
        importedAt: context.importedAt
      }
    } satisfies UmlElement;
  });

  const relationIds = new Set<string>();
  const relations = parsed.relations.flatMap((relation) => {
    const from = keyToElementId.get(relation.source);
    const to = keyToElementId.get(relation.target);
    if (!from || !to) {
      return [];
    }
    const id = uniqueId(`relation.${shortId(from)}__${relation.kind}__${shortId(to)}`, [...relationIds]);
    relationIds.add(id);
    return [
      {
        id,
        kind: relation.kind,
        from,
        to,
        name: relation.label?.trim() || relation.kind,
        stereotypes: [],
        tags: ["imported"],
        metadata: {
          ...(relation.metadata ?? {}),
          origin: "import",
          importedFrom: context.format,
          sourcePath: context.sourceRelativePath,
          importedAt: context.importedAt
        }
      } satisfies UmlRelation
    ];
  });

  const model: UmlModel = {
    schema: "umlmodel.v1",
    id: context.modelId,
    name: context.displayName,
    modelType: parsed.modelType,
    elements,
    relations,
    metadata: {
      origin: "import",
      importedFrom: context.format,
      sourcePath: context.sourceRelativePath,
      importedAt: context.importedAt,
      originalSourcePath: context.sourcePath
    }
  };

  const diagram: UmlDiagram = {
    schema: "umldiagram.v1",
    id: context.diagramId,
    name: `${context.displayName} Diagram`,
    diagramType: parsed.diagramType,
    modelRefs: [context.modelId],
    elementRefs: elements.map((element) => element.id),
    relationRefs: relations.map((relation) => relation.id),
    metadata: {
      origin: "import",
      importedFrom: context.format,
      sourcePath: context.sourceRelativePath,
      importedAt: context.importedAt,
      tags: ["imported"]
    }
  };

  const layout: UmlLayout = {
    schema: "umllayout.v1",
    diagramId: context.diagramId,
    nodes: Object.fromEntries(elements.map((element, index) => [element.id, layoutForIndex(index, element.kind)])),
    edges: {}
  };

  return { model, diagram, layout, elements, relations };
}

function detectImportConflicts(
  state: Awaited<ReturnType<typeof loadWorkspace>>,
  displayName: string,
  diagramId: string,
  elements: UmlElement[]
): ImportConflict[] {
  const conflicts: ImportConflict[] = [];
  const existingByNameKind = new Map<string, string>();

  for (const model of state.models) {
    for (const element of model.data.elements) {
      existingByNameKind.set(`${element.kind}:${element.name.toLowerCase()}`, element.id);
    }
  }

  for (const element of elements) {
    const key = `${element.kind}:${element.name.toLowerCase()}`;
    const existingId = existingByNameKind.get(key);
    if (existingId && existingId !== element.id) {
      conflicts.push({
        type: "element_name_kind",
        importedName: element.name,
        importedKind: element.kind,
        existingId,
        message: `Element "${element.name}" (${element.kind}) already exists as ${existingId}.`
      });
    }
  }

  if (state.models.some((model) => model.data.name.toLowerCase() === displayName.toLowerCase())) {
    conflicts.push({
      type: "model_name",
      importedName: displayName,
      message: `A model named "${displayName}" already exists in the workspace.`
    });
  }

  if (state.diagrams.some((diagram) => diagram.data.id === diagramId)) {
    conflicts.push({
      type: "diagram_id",
      existingId: diagramId,
      message: `Diagram id "${diagramId}" already exists in the workspace.`
    });
  }

  return conflicts;
}

function collectImportWrites(
  before: Awaited<ReturnType<typeof loadWorkspace>>,
  after: Awaited<ReturnType<typeof loadWorkspace>>,
  root: string,
  state: Awaited<ReturnType<typeof loadWorkspace>>
): Array<{ file: string; data: unknown }> {
  const writes: Array<{ file: string; data: unknown }> = [];
  const modelsDir = state.manifest?.paths.models ?? "models";
  const diagramsDir = state.manifest?.paths.diagrams ?? "diagrams";
  const layoutsDir = state.manifest?.paths.layouts ?? "layouts";

  for (const afterModel of after.models) {
    const beforeModel = before.models.find((entry) => entry.data.id === afterModel.data.id);
    if (!beforeModel || JSON.stringify(beforeModel.data) !== JSON.stringify(afterModel.data)) {
      const file =
        afterModel.file ||
        safeJoin(root, modelsDir, `${sanitizeFileName(afterModel.data.id)}.umlmodel.json`);
      writes.push({ file, data: afterModel.data });
    }
  }

  for (const afterDiagram of after.diagrams) {
    const beforeDiagram = before.diagrams.find((entry) => entry.data.id === afterDiagram.data.id);
    if (!beforeDiagram || JSON.stringify(beforeDiagram.data) !== JSON.stringify(afterDiagram.data)) {
      const file =
        afterDiagram.file ||
        safeJoin(root, diagramsDir, `${sanitizeFileName(afterDiagram.data.id)}.diagram.json`);
      writes.push({ file, data: afterDiagram.data });
    }
  }

  for (const afterLayout of after.layouts) {
    const beforeLayout = before.layouts.find((entry) => entry.data.diagramId === afterLayout.data.diagramId);
    if (!beforeLayout || JSON.stringify(beforeLayout.data) !== JSON.stringify(afterLayout.data)) {
      const file =
        afterLayout.file ||
        safeJoin(root, layoutsDir, `${sanitizeFileName(afterLayout.data.diagramId)}.layout.json`);
      writes.push({ file, data: afterLayout.data });
    }
  }

  return writes;
}

interface ParsedElement {
  key: string;
  kind: ElementKind;
  name: string;
  metadata?: Record<string, unknown>;
}

interface ParsedDiagram {
  elements: ParsedElement[];
  relations: Array<{ source: string; target: string }>;
}

function ensureImplicitElements(parsed: ParsedDiagram): ParsedElement[] {
  const byKey = new Map(parsed.elements.map((element) => [element.key, element]));
  for (const relation of parsed.relations) {
    if (!byKey.has(relation.source)) {
      byKey.set(relation.source, {
        key: relation.source,
        kind: "class",
        name: relation.source,
        metadata: { implicit: true }
      });
    }
    if (!byKey.has(relation.target)) {
      byKey.set(relation.target, {
        key: relation.target,
        kind: "class",
        name: relation.target,
        metadata: { implicit: true }
      });
    }
  }
  return [...byKey.values()];
}

function layoutForIndex(index: number, kind: ElementKind) {
  return {
    x: 120 + (index % 3) * 340,
    y: 120 + Math.floor(index / 3) * 220,
    width: kind === "note" ? 220 : 260,
    height: kind === "enum" ? 130 : 150
  };
}

function uniqueId(base: string, existingIds: string[]): string {
  const sanitized = base.replace(/[^A-Za-z0-9_.:-]+/g, "-").replace(/^-+|-+$/g, "") || "id";
  const existing = new Set(existingIds);
  if (!existing.has(sanitized)) {
    return sanitized;
  }
  let index = 2;
  while (existing.has(`${sanitized}${index}`)) {
    index += 1;
  }
  return `${sanitized}${index}`;
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

function shortId(value: string): string {
  return value.split(".").at(-1)?.replace(/[^A-Za-z0-9_-]+/g, "") || value;
}

function normalizedText(value: string): string {
  return value.endsWith("\n") ? value : `${value}\n`;
}
