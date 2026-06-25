import { describe, it, expect } from "vitest";
import { validateGeometry } from "./geometry";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";
import golden from "../../../../TrackShape/goldens/daytona.metrics.json";

describe("validateGeometry", () => {
  it("flags the example's two sharp corners (matches golden max angle)", () => {
    const w = validateGeometry(parseTrackShape(example)).filter((d) => d.code === "sharp_corner");
    expect(w.length).toBe(2);
    expect(Math.max(...w.map((d) => d.angleDeg!))).toBeCloseTo(golden.max_angle_step_deg, 1);
  });

  it("flags a handle coincident with its anchor", () => {
    const bad = structuredClone(example) as Record<string, unknown>;
    const segments = bad.segments as Record<string, unknown>[];
    const bz = segments.find((s) => (s as { type: string }).type === "bezier") as Record<string, unknown>;
    const anchors = bad.anchors as Record<string, unknown>[];
    const a = anchors.find((x) => x.id === bz.from) as Record<string, number>;
    bz.handle_from = { x: a.x, y: a.y, z: 0 };
    expect(validateGeometry(bad as ReturnType<typeof parseTrackShape>).map((d) => d.code)).toContain(
      "degenerate_handle",
    );
  });
});
