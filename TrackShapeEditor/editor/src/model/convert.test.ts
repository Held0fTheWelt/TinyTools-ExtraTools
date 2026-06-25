import { describe, it, expect } from "vitest";
import { toBezier, toLine } from "./convert";
import type { TrackShape } from "./shape";

const doc: TrackShape = {
  schema: "track_shape.v1",
  name: "t",
  closed: false,
  units: {
    source_unit: "meter",
    unreal_unit: "centimeter",
    scale_to_target_length: false,
    scale_mode: "none",
  },
  sampling: {},
  mesh: {},
  anchors: [
    { id: "a", x: 0, y: 0 },
    { id: "b", x: 30, y: 0 },
  ],
  segments: [{ id: "s", type: "line", from: "a", to: "b" }],
} as TrackShape;

describe("segment conversion", () => {
  it("line → bezier initializes handles at 1/3 and 2/3", () => {
    const seg = toBezier(doc, "s").segments[0] as Extract<TrackShape["segments"][number], { type: "bezier" }>;
    expect(seg.type).toBe("bezier");
    expect(seg.handle_from).toEqual({ x: 10, y: 0, z: 0 });
    expect(seg.handle_to).toEqual({ x: 20, y: 0, z: 0 });
  });

  it("bezier → line drops handles, keeps topology", () => {
    const bz = toBezier(doc, "s");
    const seg = toLine(bz, "s").segments[0];
    expect(seg.type).toBe("line");
    expect("handle_from" in seg).toBe(false);
    expect(seg.from).toBe("a");
    expect(seg.to).toBe("b");
  });
});
