import type { Diagnostic, RelationKind, UmlModel } from "@aiagmw/shared";
import { endpointId } from "../workspaceHelpers";
import type { ArchitectureRules, ForbiddenDependencyRule } from "./rulesLoader";

const packageDependencyKinds = new Set<RelationKind>(["dependency", "uses", "containment", "association"]);

export function detectArchitectureDiagnostics(
  models: Array<{ data: UmlModel; relativePath: string }>,
  rules: ArchitectureRules
): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];

  for (const model of models) {
    diagnostics.push(...detectPackageDependencyCycles(model.data, model.relativePath));
    diagnostics.push(...detectForbiddenDependencies(model.data, model.relativePath, rules.forbiddenDependencies ?? []));
  }

  return diagnostics;
}

function detectPackageDependencyCycles(model: UmlModel, file: string): Diagnostic[] {
  const packages = model.elements.filter((element) => element.kind === "package" || element.kind === "layer");
  if (packages.length === 0) {
    return [];
  }

  const packageIds = new Set(packages.map((entry) => entry.id));
  const graph = new Map<string, string[]>();

  for (const relation of model.relations) {
    if (!packageDependencyKinds.has(relation.kind)) {
      continue;
    }

    const from = endpointId(relation.from);
    const to = endpointId(relation.to);
    if (!packageIds.has(from) || !packageIds.has(to) || from === to) {
      continue;
    }

    const edges = graph.get(from) ?? [];
    edges.push(to);
    graph.set(from, edges);
  }

  const visited = new Set<string>();
  const stack = new Set<string>();
  const diagnostics: Diagnostic[] = [];

  const visit = (node: string, path: string[]): void => {
    if (stack.has(node)) {
      const cycleStart = path.indexOf(node);
      const cycle = [...path.slice(cycleStart), node].join(" -> ");
      diagnostics.push({
        level: "warning",
        code: "validation.package_dependency_cycle",
        message: `Package dependency cycle in model ${model.id}: ${cycle}`,
        file,
        targetId: node,
        category: "validation"
      });
      return;
    }
    if (visited.has(node)) {
      return;
    }

    visited.add(node);
    stack.add(node);
    for (const next of graph.get(node) ?? []) {
      visit(next, [...path, node]);
    }
    stack.delete(node);
  };

  for (const node of graph.keys()) {
    visit(node, []);
  }

  return diagnostics;
}

function detectForbiddenDependencies(
  model: UmlModel,
  file: string,
  rules: ForbiddenDependencyRule[]
): Diagnostic[] {
  if (rules.length === 0) {
    return [];
  }

  const elementTags = new Map<string, Set<string>>();
  for (const element of model.elements) {
    const tags = new Set<string>([...(element.tags ?? []), ...metadataTags(element.metadata)]);
    elementTags.set(element.id, tags);
  }

  const diagnostics: Diagnostic[] = [];

  for (const relation of model.relations) {
    if (!packageDependencyKinds.has(relation.kind)) {
      continue;
    }

    const fromTags = elementTags.get(endpointId(relation.from)) ?? new Set<string>();
    const toTags = elementTags.get(endpointId(relation.to)) ?? new Set<string>();

    for (const rule of rules) {
      if (!fromTags.has(rule.fromTag) || !toTags.has(rule.toTag)) {
        continue;
      }

      diagnostics.push({
        level: rule.severity ?? "warning",
        code: "validation.forbidden_dependency",
        message: `Forbidden dependency from tag "${rule.fromTag}" to "${rule.toTag}" via relation ${relation.id}.`,
        file,
        targetId: relation.id,
        category: "validation"
      });
    }
  }

  return diagnostics;
}

function metadataTags(metadata: Record<string, unknown> | undefined): string[] {
  const tags = metadata?.tags;
  return Array.isArray(tags) ? tags.filter((tag): tag is string => typeof tag === "string") : [];
}
