import { describe, it, expect } from "vitest";
import { meshPieceEstimate, meshBoundaries } from "./mesh";

describe("mesh estimate", () => {
  it("piece count is ceil(length / piece_length)", () => {
    expect(meshPieceEstimate(4000, 20)).toBe(200);
    expect(meshPieceEstimate(4001, 20)).toBe(201);
  });

  it("boundaries land every piece_length along distance", () => {
    const b = meshBoundaries(
      [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
      ],
      25,
    );
    expect(b.map((p) => p.x)).toEqual([25, 50, 75]);
  });
});
