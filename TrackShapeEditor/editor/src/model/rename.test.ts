import { describe, it, expect } from "vitest";
import { renameAnchor } from "./rename";
import { parseTrackShape } from "./shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("renameAnchor", () => {
  const doc = parseTrackShape(example);

  it("rewrites all segment references", () => {
    const old = doc.anchors[0].id;
    const next = renameAnchor(doc, old, "renamed_anchor");
    expect(next.anchors.some((a) => a.id === "renamed_anchor")).toBe(true);
    expect(next.segments.every((s) => s.from !== old && s.to !== old)).toBe(true);
  });

  it("rejects a duplicate id", () => {
    expect(() => renameAnchor(doc, doc.anchors[0].id, doc.anchors[1].id)).toThrow();
  });
});
