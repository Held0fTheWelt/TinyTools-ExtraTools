import { describe, it, expect } from "vitest";
import { parseTrackShape } from "./shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("parseTrackShape", () => {
  it("accepts the shipped example", () => {
    const shape = parseTrackShape(example);
    expect(shape.schema).toBe("track_shape.v1");
    expect(shape.anchors.length).toBeGreaterThan(0);
    expect(shape.segments.length).toBeGreaterThan(0);
  });

  it("rejects an unknown top-level field", () => {
    expect(() => parseTrackShape({ ...example, bogus: 1 })).toThrow();
  });

  it("rejects a line segment carrying bezier handles", () => {
    const bad = structuredClone(example) as Record<string, unknown>;
    const segments = bad.segments as Record<string, unknown>[];
    segments[0] = { ...segments[0], type: "line", handle_from: { x: 0, y: 0 } };
    expect(() => parseTrackShape(bad)).toThrow();
  });

  it("accepts an additional pit lane layout", () => {
    const doc = structuredClone(example) as Record<string, unknown>;
    doc.layouts = [
      {
        id: "PitLane",
        label: "Pit Lane",
        kind: "pit_lane",
        closed: false,
        anchors: [
          { id: "pit_a", x: 0, y: 25, z: 0 },
          { id: "pit_b", x: 100, y: 25, z: 0 },
        ],
        segments: [{ id: "pit_seg", type: "line", from: "pit_a", to: "pit_b", samples: 1 }],
      },
    ];
    const shape = parseTrackShape(doc);
    expect(shape.layouts?.[0].kind).toBe("pit_lane");
  });
});
