import type { Diagnostic, RelationKind, UmlModel } from "@aiagmw/shared";
import { endpointId } from "../workspaceHelpers";

const inheritanceKinds = new Set<RelationKind>(["inheritance", "implementation", "realization"]);
const compositionKinds = new Set<RelationKind>(["composition"]);

export function detectCycleDiagnostics(models: Array<{ data: UmlModel; relativePath: string }>): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];

  for (const model of models) {
    diagnostics.push(...detectRelationCycles(model.data, model.relativePath, inheritanceKinds, "validation.inheritance_cycle"));
    diagnostics.push(...detectRelationCycles(model.data, model.relativePath, compositionKinds, "validation.composition_cycle"));
  }

  return diagnostics;
}

function detectRelationCycles(
  model: UmlModel,
  file: string,
  kinds: Set<RelationKind>,
  code: string
): Diagnostic[] {
  const graph = new Map<string, string[]>();

  for (const relation of model.relations) {
    if (!kinds.has(relation.kind)) {
      continue;
    }
    const from = endpointId(relation.from);
    const to = endpointId(relation.to);
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
        level: "error",
        code,
        message: `Cycle detected in model ${model.id}: ${cycle}`,
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
