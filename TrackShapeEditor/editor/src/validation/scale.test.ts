import { describe, it, expect } from "vitest";
import { scalePreview } from "./scale";

describe("scalePreview", () => {
  it("computes factor = target/raw and the example shrinks", () => {
    const r = scalePreview(4098.3, 4000);
    expect(r.factor).toBeCloseTo(0.97601, 4);
    expect(r.warn).toBe(false);
  });

  it("warns when factor is outside [0.75, 1.25]", () => {
    expect(scalePreview(1000, 4000).warn).toBe(true);
  });
});
