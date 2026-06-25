import { describe, expect, it } from "vitest";
import type { TrackShape } from "./shape";
import { smoothTrackShape } from "./smooth";
import { bezierDeriv } from "../geometry/bezier";
import { norm } from "../geometry/vec";

const doc: TrackShape = {
  schema: "track_shape.v1",
  name: "test",
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
    { id: "c", x: 30, y: 30 },
  ],
  segments: [
    { id: "s1", type: "line", from: "a", to: "b" },
    { id: "s2", type: "line", from: "b", to: "c" },
  ],
};

describe("smoothTrackShape", () => {
  it("keeps anchors fixed and converts hard joins into continuous beziers", () => {
    const smoothed = smoothTrackShape(doc);
    expect(smoothed.anchors).toEqual(doc.anchors);
    expect(smoothed.segments.every((s) => s.type === "bezier")).toBe(true);

    const first = smoothed.segments[0];
    const second = smoothed.segments[1];
    if (first.type !== "bezier" || second.type !== "bezier") throw new Error("expected beziers");

    const a = { x: 0, y: 0 };
    const b = { x: 30, y: 0 };
    const c = { x: 30, y: 30 };
    const incoming = norm(bezierDeriv(a, first.handle_from, first.handle_to, b, 1));
    const outgoing = norm(bezierDeriv(b, second.handle_from, second.handle_to, c, 0));
    const dot = incoming.x * outgoing.x + incoming.y * outgoing.y;

    expect(dot).toBeGreaterThan(0.999);
  });

  it("removes redundant anchors on an almost straight section", () => {
    const almostStraight: TrackShape = {
      ...doc,
      anchors: [
        { id: "a", x: 0, y: 0 },
        { id: "b", x: 10, y: 0.1 },
        { id: "c", x: 20, y: 0 },
      ],
      segments: [
        { id: "s1", type: "line", from: "a", to: "b" },
        { id: "s2", type: "line", from: "b", to: "c" },
      ],
    };

    const smoothed = smoothTrackShape(almostStraight);

    expect(smoothed.anchors.map((a) => a.id)).toEqual(["a", "c"]);
    expect(smoothed.segments).toHaveLength(1);
    expect(smoothed.metadata?.smoothing).toMatchObject({ removed_anchor_count: 1 });
  });

  it("moves mild outlier anchors toward the local course", () => {
    const jitter: TrackShape = {
      ...doc,
      anchors: [
        { id: "a", x: 0, y: 0 },
        { id: "b", x: 10, y: 2 },
        { id: "c", x: 20, y: 0 },
        { id: "d", x: 30, y: 0 },
      ],
      segments: [
        { id: "s1", type: "line", from: "a", to: "b" },
        { id: "s2", type: "line", from: "b", to: "c" },
        { id: "s3", type: "line", from: "c", to: "d" },
      ],
    };

    const smoothed = smoothTrackShape(jitter);
    const b = smoothed.anchors.find((a) => a.id === "b")!;

    expect(b.y).toBeLessThan(2);
    expect(smoothed.metadata?.smoothing).toMatchObject({ moved_anchor_count: expect.any(Number) });
  });
});
