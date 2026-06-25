import { describe, it, expect } from "vitest";
import { mapAnchor, mapSegment, incidentBezierHandles } from "./edit";
import { parseTrackShape } from "./shape";
import example from "../../test/fixtures/daytona_shape.example.json";

const doc = parseTrackShape(example);

describe("edit helpers", () => {
  it("mapAnchor returns a new doc with one anchor changed, others identical", () => {
    const id = doc.anchors[0].id;
    const next = mapAnchor(doc, id, (a) => ({ ...a, x: a.x + 5 }));
    expect(next).not.toBe(doc);
    expect(next.anchors[0].x).toBe(doc.anchors[0].x + 5);
    expect(next.anchors[1]).toBe(doc.anchors[1]);
  });

  it("incidentBezierHandles lists handles touching an anchor", () => {
    const bz = doc.segments.find((s) => s.type === "bezier")!;
    const hs = incidentBezierHandles(doc, bz.from);
    expect(hs.some((h) => h.segId === bz.id && h.end === "from")).toBe(true);
  });
});
