import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Viewport } from "./Viewport";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("Viewport overlays", () => {
  it("renders mesh boundary ticks when overlay enabled", () => {
    const shape = parseTrackShape(example);
    const { container } = render(<Viewport shape={shape} showMeshTicks pieceLengthM={20} />);
    expect(container.querySelectorAll("[data-mesh-tick]").length).toBeGreaterThan(0);
  });
});
