import { describe, it, expect } from "vitest";
import { validateTopology } from "./topology";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("validateTopology", () => {
  it("the shipped example is topologically clean", () => {
    expect(validateTopology(parseTrackShape(example))).toEqual([]);
  });

  it("flags a disconnected chain", () => {
    const bad = structuredClone(example) as Record<string, unknown>;
    const segments = bad.segments as Record<string, unknown>[];
    segments[1].from = (segments[0] as Record<string, unknown>).from;
    const codes = validateTopology(bad as ReturnType<typeof parseTrackShape>).map((d) => d.code);
    expect(codes).toContain("chain_disconnected");
  });

  it("flags a missing anchor reference", () => {
    const bad = structuredClone(example) as Record<string, unknown>;
    const segments = bad.segments as Record<string, unknown>[];
    segments[0].from = "does_not_exist";
    expect(validateTopology(bad as ReturnType<typeof parseTrackShape>).map((d) => d.code)).toContain(
      "missing_anchor_ref",
    );
  });
});
