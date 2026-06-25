import { describe, it, expect } from "vitest";
import { sampleShape, polylineLength, boundingBox } from "./metrics";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";
import golden from "../../../../TrackShape/goldens/daytona.metrics.json";

describe("metrics vs shared golden", () => {
  const shape = parseTrackShape(example);
  const pts = sampleShape(shape);

  it("raw length matches golden within tolerance", () => {
    expect(Math.abs(polylineLength(pts) - golden.raw_length_m)).toBeLessThan(golden.tolerance.length_m);
  });

  it("bounding box matches golden", () => {
    const bb = boundingBox(pts);
    expect(Math.abs(bb.w - golden.bbox_w_m)).toBeLessThan(golden.tolerance.bbox_m);
    expect(Math.abs(bb.h - golden.bbox_h_m)).toBeLessThan(golden.tolerance.bbox_m);
  });
});
