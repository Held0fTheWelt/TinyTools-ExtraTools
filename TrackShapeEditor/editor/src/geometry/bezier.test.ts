import { describe, it, expect } from "vitest";
import { bezierPoint, bezierDeriv } from "./bezier";

const P0 = { x: 0, y: 0 };
const P1 = { x: 0, y: 10 };
const P2 = { x: 10, y: 10 };
const P3 = { x: 10, y: 0 };

describe("cubic bezier", () => {
  it("hits the endpoints", () => {
    expect(bezierPoint(P0, P1, P2, P3, 0)).toEqual({ x: 0, y: 0 });
    expect(bezierPoint(P0, P1, P2, P3, 1)).toEqual({ x: 10, y: 0 });
  });

  it("derivative at t=0 equals 3*(P1-P0)", () => {
    const d = bezierDeriv(P0, P1, P2, P3, 0);
    expect(d.x).toBeCloseTo(0, 9);
    expect(d.y).toBeCloseTo(30, 9);
  });
});
