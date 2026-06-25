import type { ElementKind, PatchPreviewResponse, RelationKind, UmlMethod } from "@aiagmw/shared";
import type { DiagramCanvasVariant } from "./BaseDiagramCanvas";

export type DiffElementState = "added" | "removed" | "updated";

export function buildDiffElementStates(preview: PatchPreviewResponse | null): Map<string, DiffElementState> {
  const states = new Map<string, DiffElementState>();
  if (!preview) {
    return states;
  }
  for (const entry of preview.diff.addedElements) {
    states.set(entry.element.id, "added");
  }
  for (const entry of preview.diff.removedElements) {
    states.set(entry.element.id, "removed");
  }
  for (const entry of preview.diff.updatedElements) {
    states.set(entry.elementId, "updated");
  }
  return states;
}

export function nodeClassName(
  element: { kind: ElementKind },
  selected: boolean | undefined,
  diffState?: DiffElementState,
  variant?: DiagramCanvasVariant
): string {
  const classes = ["uml-node", element.kind];
  if (variant) {
    classes.push(`variant-${variant}`);
  }
  if (selected) {
    classes.push("selected");
  }
  if (diffState) {
    classes.push(`diff-${diffState}`);
  }
  return classes.join(" ");
}

export function endpointId(value: string): string {
  const index = value.indexOf("#");
  return index >= 0 ? value.slice(index + 1) : value;
}

export function relationLabel(relation: {
  name?: string;
  kind: RelationKind;
  fromMultiplicity?: string;
  toMultiplicity?: string;
}): string {
  const parts = [relation.name ?? relation.kind];
  if (relation.fromMultiplicity || relation.toMultiplicity) {
    parts.push(`${relation.fromMultiplicity ?? ""} .. ${relation.toMultiplicity ?? ""}`);
  }
  return parts.join(" ");
}

export function formatParameters(parameters: UmlMethod["parameters"] = []): string {
  return parameters.map((parameter) => `${parameter.name}${parameter.type ? `: ${parameter.type}` : ""}`).join(", ");
}

export function visibilitySymbol(value: string | undefined): string {
  switch (value) {
    case "public":
      return "+ ";
    case "private":
      return "- ";
    case "protected":
      return "# ";
    case "package":
      return "~ ";
    default:
      return "";
  }
}
