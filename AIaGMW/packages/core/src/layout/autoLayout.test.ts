import { describe, expect, it } from "vitest";
import { autoLayout } from "./autoLayout";

describe("autoLayout", () => {
  it("arranges nodes in a simple grid", () => {
    const layout = autoLayout(
      ["a", "b", "c", "d"],
      {
        schema: "umllayout.v1",
        diagramId: "diagram.test",
        nodes: {},
        edges: {}
      },
      { columns: 2, cellWidth: 100, cellHeight: 80, paddingX: 10, paddingY: 20 }
    );

    expect(layout.nodes.a).toEqual({ x: 10, y: 20, width: 260, height: 150 });
    expect(layout.nodes.b).toEqual({ x: 110, y: 20, width: 260, height: 150 });
    expect(layout.nodes.c).toEqual({ x: 10, y: 100, width: 260, height: 150 });
    expect(layout.nodes.d).toEqual({ x: 110, y: 100, width: 260, height: 150 });
  });
});
