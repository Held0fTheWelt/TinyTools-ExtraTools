import type { NodeLayout, UmlLayout } from "@aiagmw/shared";

export interface AutoLayoutOptions {
  columns?: number;
  cellWidth?: number;
  cellHeight?: number;
  paddingX?: number;
  paddingY?: number;
}

export function autoLayout(
  elementIds: string[],
  existingLayout: UmlLayout,
  options: AutoLayoutOptions = {}
): UmlLayout {
  const columns = options.columns ?? 3;
  const cellWidth = options.cellWidth ?? 300;
  const cellHeight = options.cellHeight ?? 200;
  const paddingX = options.paddingX ?? 80;
  const paddingY = options.paddingY ?? 80;

  const nodes: Record<string, NodeLayout> = { ...existingLayout.nodes };

  for (const [index, elementId] of elementIds.entries()) {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const current: NodeLayout = nodes[elementId] ?? { x: 0, y: 0 };
    nodes[elementId] = {
      ...current,
      x: paddingX + column * cellWidth,
      y: paddingY + row * cellHeight,
      width: current.width ?? 260,
      height: current.height ?? 150
    };
  }

  return {
    ...existingLayout,
    nodes
  };
}
