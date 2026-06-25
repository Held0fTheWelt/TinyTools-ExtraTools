import type { DiagramType, ElementKind, RelationKind } from "@aiagmw/shared";

export interface DiagramPalette {
  elementKinds: ElementKind[];
  relationKinds: RelationKind[];
}

const classPalette: DiagramPalette = {
  elementKinds: ["class", "abstract_class", "interface", "enum", "note"],
  relationKinds: ["association", "dependency", "inheritance", "implementation", "aggregation", "composition"]
};

const packagePalette: DiagramPalette = {
  elementKinds: ["package", "layer", "note"],
  relationKinds: ["dependency", "containment", "association"]
};

const componentPalette: DiagramPalette = {
  elementKinds: ["component", "interface", "layer", "note"],
  relationKinds: ["dependency", "realization", "uses", "association"]
};

const sequencePalette: DiagramPalette = {
  elementKinds: ["lifeline", "activation", "fragment", "actor", "note"],
  relationKinds: ["sync_message", "async_message", "reply", "destroy"]
};

const statePalette: DiagramPalette = {
  elementKinds: ["state_node", "pseudostate", "final_state", "note"],
  relationKinds: ["transition"]
};

const activityPalette: DiagramPalette = {
  elementKinds: ["action", "decision", "merge", "fork", "join", "note"],
  relationKinds: ["control_flow", "object_flow"]
};

const deploymentPalette: DiagramPalette = {
  elementKinds: ["node", "artifact", "deployment_spec", "component", "note"],
  relationKinds: ["deploy", "communicate", "dependency"]
};

const mixedPalette: DiagramPalette = {
  elementKinds: ["class", "component", "package", "interface", "note"],
  relationKinds: ["association", "dependency", "inheritance", "containment"]
};

const palettes: Record<DiagramType, DiagramPalette> = {
  class: classPalette,
  package: packagePalette,
  component: componentPalette,
  sequence: sequencePalette,
  state: statePalette,
  activity: activityPalette,
  deployment: deploymentPalette,
  mixed: mixedPalette
};

export function getPaletteForDiagramType(diagramType: DiagramType): DiagramPalette {
  return palettes[diagramType] ?? classPalette;
}
