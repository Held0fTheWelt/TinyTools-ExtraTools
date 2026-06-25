import type {
  DiagramExportResult,
  DiagramImportRequest,
  DiagramImportResult,
  DiagramExportFormat,
  DiagramImportFormat
} from "./importExportTypes";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type {
  DiagramDetail,
  DiagramType,
  ElementKind,
  ModelType,
  RelationKind,
  UmlElement
} from "@aiagmw/shared";
import { getDiagramDetail, loadWorkspace, type LoadWorkspaceOptions } from "./workspace";
import { relativePath, safeJoin, sanitizeFileName } from "./workspacePaths";
import { applyImportPatchBuild, buildImportPatch } from "./import/importPatch";
import { submitProposal } from "./workspace";
import { simulatePatch } from "./patch/simulatePatch";
import { generateDiff } from "./patch/generateDiff";

export type {
  DiagramImportFormat,
  DiagramExportFormat,
  DiagramImportRequest,
  DiagramImportResult,
  DiagramExportResult
} from "./importExportTypes";

interface ParsedElement {
  key: string;
  kind: ElementKind;
  name: string;
  metadata?: Record<string, unknown>;
}

interface ParsedRelation {
  source: string;
  target: string;
  kind: RelationKind;
  label?: string;
  metadata?: Record<string, unknown>;
}

interface ParsedDiagram {
  name: string;
  diagramType: DiagramType;
  modelType: ModelType;
  elements: ParsedElement[];
  relations: ParsedRelation[];
}

const plantUmlElementRe =
  /^\s*(?<kind>abstract\s+class|class|interface|enum|actor|usecase|state|participant|database|queue|object|component|package|note)\s+(?<name>"[^"]+"|[A-Za-z0-9_.:/ -]+?)(?:\s+as\s+(?<alias>[A-Za-z0-9_.:-]+))?(?:\s+<<(?<stereotype>[^>]+)>>)?\s*(?:\{)?\s*$/i;
const plantUmlRelationRe =
  /^\s*(?<source>"[^"]+"|[A-Za-z0-9_.:-]+)\s+(?<arrow>[.<|*o+]?[-.=]+[->.<|*o+]+|-->|->|<--|<-|--|\.\.>)\s+(?<target>"[^"]+"|[A-Za-z0-9_.:-]+)(?:\s*:\s*(?<label>.*))?\s*$/;
const plantUmlTitleRe = /^\s*title\s+(?<title>.+?)\s*$/i;
const mermaidTitleRe = /^\s*%%\s*title\s*:\s*(?<title>.+?)\s*$/i;
const mermaidClassRe = /^\s*class\s+(?<name>[A-Za-z0-9_.:-]+)/;
const mermaidClassRelationRe =
  /^\s*(?<source>[A-Za-z0-9_.:-]+)\s+(?<arrow><\|--|--\|>|\.\.\|>|\*--|--\*|o--|--o|-->|->|\.\.>|--)\s+(?<target>[A-Za-z0-9_.:-]+)(?:\s*:\s*(?<label>.*))?\s*$/;
const mermaidFlowNodeRe = /(?<id>[A-Za-z0-9_]+)(?:\[(?:"(?<quoted>[^"]+)"|(?<label>[^\]]+))\])/g;
const mermaidFlowRelationRe =
  /^\s*(?<source>[A-Za-z0-9_]+)(?:\[[^\]]+\])?\s*[-.=]+>\s*(?:\|(?<label>[^|]+)\|)?\s*(?<target>[A-Za-z0-9_]+)(?:\[[^\]]+\])?/;

export interface ImportDiagramPatchResult {
  proposal: Awaited<ReturnType<typeof buildImportPatch>>["proposal"];
  conflicts: Awaited<ReturnType<typeof buildImportPatch>>["conflicts"];
  sourceRelativePath: string;
  imported: Awaited<ReturnType<typeof buildImportPatch>>["imported"];
  preview: ReturnType<typeof generateDiff> | null;
  applicable: boolean;
}

export async function importDiagramAsPatch(
  options: LoadWorkspaceOptions,
  input: DiagramImportRequest,
  submit = false
): Promise<ImportDiagramPatchResult & { summary?: Awaited<ReturnType<typeof submitProposal>> }> {
  const built = await buildImportPatch(options, input);
  const state = await loadWorkspace(options);
  const simulation = simulatePatch(state, built.proposal);

  const result: ImportDiagramPatchResult & { summary?: Awaited<ReturnType<typeof submitProposal>> } = {
    proposal: built.proposal,
    conflicts: built.conflicts,
    sourceRelativePath: built.sourceRelativePath,
    imported: built.imported,
    preview: simulation.applicable ? generateDiff(simulation.before, simulation.after, built.proposal) : null,
    applicable: simulation.applicable
  };

  if (submit) {
    result.summary = await submitProposal(options, built.proposal);
  }

  return result;
}

export async function previewImportDiagramPatch(
  options: LoadWorkspaceOptions,
  input: DiagramImportRequest
): Promise<ImportDiagramPatchResult> {
  return importDiagramAsPatch(options, input, false);
}

export async function importDiagramSource(
  options: LoadWorkspaceOptions,
  input: DiagramImportRequest
): Promise<DiagramImportResult> {
  const built = await buildImportPatch(options, input);
  const applied = await applyImportPatchBuild(options, built, input.source);
  return {
    model: applied.model,
    diagram: applied.diagram,
    layout: applied.layout,
    sourcePath: applied.sourcePath,
    imported: applied.imported
  };
}

export async function exportDiagramSource(
  options: LoadWorkspaceOptions,
  diagramId: string,
  format: DiagramExportFormat
): Promise<DiagramExportResult> {
  const state = await loadWorkspace(options);
  const detail = getDiagramDetail(state, diagramId);
  if (!detail) {
    throw new Error(`Diagram ${diagramId} was not found.`);
  }
  const source =
    format === "plantuml"
      ? renderPlantUml(detail)
      : detail.diagram.diagramType === "class"
        ? renderMermaidClassDiagram(detail)
        : renderMermaidFlowchart(detail);
  const exportsDir = state.manifest?.paths.exports ?? "exports";
  const extension = format === "plantuml" ? "puml" : "mmd";
  const file = safeJoin(state.root, exportsDir, `${sanitizeFileName(detail.diagram.id)}.${extension}`);
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, normalizedText(source), "utf8");
  return {
    format,
    diagramId,
    path: relativePath(state.root, file),
    source: normalizedText(source)
  };
}

export function parsePlantUml(source: string): ParsedDiagram {
  const elements = new Map<string, ParsedElement>();
  const relations: ParsedRelation[] = [];
  let name = "Imported PlantUML";

  for (const line of source.split(/\r?\n/)) {
    const title = plantUmlTitleRe.exec(line);
    if (title?.groups?.title) {
      name = title.groups.title.trim();
      continue;
    }

    const elementMatch = plantUmlElementRe.exec(line);
    if (elementMatch?.groups?.name && elementMatch.groups.kind) {
      const rawName = unquote(elementMatch.groups.name);
      const key = elementMatch.groups.alias || rawName;
      const parsedKind = plantUmlKind(elementMatch.groups.kind);
      elements.set(key, {
        key,
        kind: parsedKind.kind,
        name: rawName,
        metadata: {
          sourceLine: line,
          stereotype: elementMatch.groups.stereotype,
          ...(parsedKind.parsedKind ? { parsedKind: parsedKind.parsedKind } : {})
        }
      });
      continue;
    }

    const relationMatch = plantUmlRelationRe.exec(line);
    if (relationMatch?.groups?.source && relationMatch.groups.target && relationMatch.groups.arrow) {
      relations.push({
        source: unquote(relationMatch.groups.source),
        target: unquote(relationMatch.groups.target),
        kind: relationKindFromArrow(relationMatch.groups.arrow),
        label: relationMatch.groups.label,
        metadata: {
          sourceLine: line,
          arrow: relationMatch.groups.arrow
        }
      });
    }
  }

  const elementList = [...elements.values()];
  return {
    name,
    diagramType: detectDiagramType(source, elementList),
    modelType: detectModelType(elementList),
    elements: elementList,
    relations
  };
}

export function parseMermaid(source: string): ParsedDiagram {
  const lines = source.split(/\r?\n/);
  const firstMeaningfulLine = lines.find((line) => line.trim() && !line.trim().startsWith("%%"))?.trim().toLowerCase() ?? "";
  let name = "Imported Mermaid";
  for (const line of lines) {
    const title = mermaidTitleRe.exec(line);
    if (title?.groups?.title) {
      name = title.groups.title.trim();
      break;
    }
  }
  return firstMeaningfulLine.startsWith("classdiagram")
    ? parseMermaidClassDiagram(lines, name)
    : parseMermaidFlowchart(lines, name);
}

function parseMermaidClassDiagram(lines: string[], name: string): ParsedDiagram {
  const elements = new Map<string, ParsedElement>();
  const relations: ParsedRelation[] = [];
  for (const line of lines) {
    const classMatch = mermaidClassRe.exec(line);
    if (classMatch?.groups?.name) {
      const key = classMatch.groups.name;
      elements.set(key, { key, kind: "class", name: key, metadata: { sourceLine: line } });
      continue;
    }
    const relationMatch = mermaidClassRelationRe.exec(line);
    if (relationMatch?.groups?.source && relationMatch.groups.target && relationMatch.groups.arrow) {
      relations.push({
        source: relationMatch.groups.source,
        target: relationMatch.groups.target,
        kind: relationKindFromArrow(relationMatch.groups.arrow),
        label: relationMatch.groups.label,
        metadata: { sourceLine: line, arrow: relationMatch.groups.arrow }
      });
    }
  }
  return { name, diagramType: "class", modelType: "class-model", elements: [...elements.values()], relations };
}

function parseMermaidFlowchart(lines: string[], name: string): ParsedDiagram {
  const elements = new Map<string, ParsedElement>();
  const relations: ParsedRelation[] = [];
  for (const line of lines) {
    for (const match of line.matchAll(mermaidFlowNodeRe)) {
      if (!match.groups?.id) {
        continue;
      }
      elements.set(match.groups.id, {
        key: match.groups.id,
        kind: "component",
        name: (match.groups.quoted || match.groups.label || match.groups.id).trim(),
        metadata: { sourceLine: line, mermaidId: match.groups.id }
      });
    }
    const relationMatch = mermaidFlowRelationRe.exec(line);
    if (relationMatch?.groups?.source && relationMatch.groups.target) {
      relations.push({
        source: relationMatch.groups.source,
        target: relationMatch.groups.target,
        kind: "dependency",
        label: relationMatch.groups.label,
        metadata: { sourceLine: line }
      });
    }
  }
  return { name, diagramType: "component", modelType: "component-model", elements: [...elements.values()], relations };
}

function detectDiagramType(source: string, elements: ParsedElement[]): DiagramType {
  const lower = source.toLowerCase();
  const parsedKinds = new Set(
    elements
      .map((element) => String(element.metadata?.parsedKind ?? "").toLowerCase())
      .filter(Boolean)
  );
  const kinds = new Set(elements.map((element) => element.kind));

  if (parsedKinds.has("usecase") || (parsedKinds.has("actor") && parsedKinds.has("usecase"))) {
    return "mixed";
  }
  if (parsedKinds.has("state") || lower.includes("[*]")) {
    return "mixed";
  }
  if (parsedKinds.has("participant")) {
    return "sequence";
  }
  if (parsedKinds.has("database") || parsedKinds.has("queue")) {
    return "deployment";
  }
  if (["class", "interface", "enum", "abstract_class"].some((kind) => kinds.has(kind as ElementKind))) {
    return "class";
  }
  if (kinds.has("component")) {
    return "component";
  }
  return "class";
}

function detectModelType(elements: ParsedElement[]): ModelType {
  const diagramType = detectDiagramType("", elements);
  if (diagramType === "component") {
    return "component-model";
  }
  if (diagramType === "sequence") {
    return "sequence-model";
  }
  if (diagramType === "deployment") {
    return "deployment-model";
  }
  return "class-model";
}

function renderPlantUml(detail: DiagramDetail): string {
  const aliases = new Map(detail.elements.map((element) => [element.id, aliasFor(element)]));
  const lines = ["@startuml", `title ${detail.diagram.name}`, ""];
  for (const element of detail.elements) {
    const alias = aliases.get(element.id) ?? aliasFor(element);
    lines.push(`${plantUmlKeyword(element.kind, element.metadata?.parsedKind)} ${quoteIfNeeded(element.name)} as ${alias}`);
  }
  if (detail.relations.length) {
    lines.push("");
  }
  for (const relation of detail.relations) {
    const from = aliases.get(endpointId(relation.from)) ?? aliasForId(relation.from);
    const to = aliases.get(endpointId(relation.to)) ?? aliasForId(relation.to);
    const label = relation.name ? ` : ${relation.name}` : "";
    lines.push(`${from} ${plantUmlArrow(relation.kind)} ${to}${label}`);
  }
  lines.push("@enduml");
  return lines.join("\n");
}

function renderMermaidClassDiagram(detail: DiagramDetail): string {
  const aliases = new Map(detail.elements.map((element) => [element.id, aliasFor(element)]));
  const lines = [`%% title: ${detail.diagram.name}`, "classDiagram"];
  for (const element of detail.elements) {
    const alias = aliases.get(element.id) ?? aliasFor(element);
    lines.push(`  class ${alias}`);
  }
  for (const relation of detail.relations) {
    const from = aliases.get(endpointId(relation.from)) ?? aliasForId(relation.from);
    const to = aliases.get(endpointId(relation.to)) ?? aliasForId(relation.to);
    const label = relation.name ? ` : ${relation.name}` : "";
    lines.push(`  ${from} ${mermaidClassArrow(relation.kind)} ${to}${label}`);
  }
  return lines.join("\n");
}

function renderMermaidFlowchart(detail: DiagramDetail): string {
  const aliases = new Map(detail.elements.map((element) => [element.id, aliasFor(element)]));
  const lines = [`%% title: ${detail.diagram.name}`, "flowchart LR"];
  for (const element of detail.elements) {
    const alias = aliases.get(element.id) ?? aliasFor(element);
    lines.push(`  ${alias}["${escapeMermaidLabel(element.name)}"]`);
  }
  for (const relation of detail.relations) {
    const from = aliases.get(endpointId(relation.from)) ?? aliasForId(relation.from);
    const to = aliases.get(endpointId(relation.to)) ?? aliasForId(relation.to);
    const label = relation.name || relation.kind;
    lines.push(`  ${from} -->|${escapeMermaidLabel(label)}| ${to}`);
  }
  return lines.join("\n");
}

function plantUmlKind(kind: string): { kind: ElementKind; parsedKind?: string } {
  const normalized = kind.toLowerCase().replace(/\s+/g, "_");
  const mapped: Record<string, ElementKind> = {
    abstract_class: "abstract_class",
    class: "class",
    interface: "interface",
    enum: "enum",
    component: "component",
    package: "package",
    note: "note",
    actor: "actor",
    usecase: "boundary",
    state: "component",
    participant: "actor",
    database: "node",
    queue: "service",
    object: "class"
  };
  const resolved = mapped[normalized] ?? "class";
  return resolved === normalized ? { kind: resolved } : { kind: resolved, parsedKind: normalized };
}

function plantUmlKeyword(kind: ElementKind, parsedKind?: unknown): string {
  if (typeof parsedKind === "string" && parsedKind !== kind) {
    return parsedKind.replace(/_/g, " ");
  }
  if (kind === "abstract_class") {
    return "abstract class";
  }
  if (["class", "interface", "enum", "component", "package", "note", "actor"].includes(kind)) {
    return kind;
  }
  return "class";
}

function relationKindFromArrow(arrow: string): RelationKind {
  if (arrow.includes("<|--") || arrow.includes("--|>")) {
    return "inheritance";
  }
  if (arrow.includes("..|>")) {
    return "implementation";
  }
  if (arrow.includes("*--") || arrow.includes("--*")) {
    return "composition";
  }
  if (arrow.includes("o--") || arrow.includes("--o")) {
    return "aggregation";
  }
  if (arrow.includes("..>")) {
    return "dependency";
  }
  return "association";
}

function plantUmlArrow(kind: RelationKind): string {
  const arrows: Partial<Record<RelationKind, string>> = {
    inheritance: "--|>",
    implementation: "..|>",
    realization: "..|>",
    composition: "*--",
    aggregation: "o--",
    dependency: "..>",
    calls: "->",
    uses: "..>",
    containment: "--"
  };
  return arrows[kind] ?? "--";
}

function mermaidClassArrow(kind: RelationKind): string {
  const arrows: Partial<Record<RelationKind, string>> = {
    inheritance: "<|--",
    implementation: "..|>",
    realization: "..|>",
    composition: "*--",
    aggregation: "o--",
    dependency: "..>",
    calls: "-->",
    uses: "..>",
    association: "--"
  };
  return arrows[kind] ?? "--";
}

function aliasFor(element: UmlElement): string {
  return aliasForId(element.id);
}

function aliasForId(value: string): string {
  return `N_${shortId(endpointId(value))}`;
}

function endpointId(value: string): string {
  const index = value.indexOf("#");
  return index >= 0 ? value.slice(index + 1) : value;
}

function shortId(value: string): string {
  return value.split(".").at(-1)?.replace(/[^A-Za-z0-9_-]+/g, "") || value;
}

function unquote(value: string): string {
  const trimmed = value.trim();
  return trimmed.startsWith('"') && trimmed.endsWith('"') ? trimmed.slice(1, -1) : trimmed;
}

function quoteIfNeeded(value: string): string {
  return /[^A-Za-z0-9_.:-]/.test(value) ? `"${value.replaceAll('"', '\\"')}"` : value;
}

function escapeMermaidLabel(value: string): string {
  return value.replaceAll('"', '\\"').replaceAll("|", "/");
}

function normalizedText(value: string): string {
  return value.endsWith("\n") ? value : `${value}\n`;
}
