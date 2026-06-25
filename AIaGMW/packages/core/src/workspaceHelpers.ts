import type { WorkspaceState } from "./workspace";

export function endpointId(value: string): string {
  const hashIndex = value.indexOf("#");
  return hashIndex >= 0 ? value.slice(hashIndex + 1) : value;
}

export function findElement(state: WorkspaceState, elementId: string) {
  const normalized = endpointId(elementId);
  for (const model of state.models) {
    const element = model.data.elements.find((candidate) => candidate.id === normalized);
    if (element) {
      return { model, element };
    }
  }
  return null;
}

export function findRelation(state: WorkspaceState, relationId: string) {
  for (const model of state.models) {
    const relation = model.data.relations.find((candidate) => candidate.id === relationId);
    if (relation) {
      return { model, relation };
    }
  }
  return null;
}
