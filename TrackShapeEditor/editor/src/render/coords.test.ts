import { describe, it, expect } from "vitest";
import { screenToWorld } from "./coords";

describe("screenToWorld", () => {
  const view = { vbMinX: 0, vbMinY: 0, vbW: 100, vbH: 100, pxW: 200, pxH: 200, flipY: true };

  it("maps a screen pixel to world units (Y flipped)", () => {
    expect(screenToWorld(100, 0, view)).toEqual({ x: 50, y: 100 });
    expect(screenToWorld(0, 200, view)).toEqual({ x: 0, y: 0 });
  });
});
