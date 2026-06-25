import { describe, it, expect } from "vitest";
import { segmentMetrics } from "./segmentMetrics";
import type { TrackShape } from "../model/shape";

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
    { id: "b", x: 40, y: 0 },
  ],
  segments: [{ id: "s", type: "line", from: "a", to: "b", samples: 1 }],
} as TrackShape;

describe("segmentMetrics", () => {
  it("line length is the chord", () => {
    expect(segmentMetrics(doc, "s").lengthM).toBeCloseTo(40, 6);
  });

  it("adaptive segment reports adaptive=true and ignores samples as count", () => {
    const bz = {
      id: "s",
      type: "bezier" as const,
      from: "a",
      to: "b",
      handle_from: { x: 10, y: 20 },
      handle_to: { x: 30, y: 20 },
      samples: 4,
      adaptive: true,
    };
    const d2 = { ...doc, segments: [bz] } as TrackShape;
    const m = segmentMetrics(d2, "s");
    expect(m.adaptive).toBe(true);
    expect(m.generatedPoints).toBeGreaterThan(4);
  });
});
