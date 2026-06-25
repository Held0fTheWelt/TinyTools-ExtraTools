import { describe, it, expect } from "vitest";
import { serializeShape, deserializeShape } from "./file";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("save/load roundtrip", () => {
  it("serialize → deserialize returns an equal document", () => {
    const doc = parseTrackShape(example);
    expect(deserializeShape(serializeShape(doc))).toEqual(doc);
  });

  it("serialized JSON is stable (sorted keys, 2-space)", () => {
    const doc = parseTrackShape(example);
    expect(serializeShape(doc)).toBe(serializeShape(deserializeShape(serializeShape(doc))));
  });
});
