import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Viewport } from "./Viewport";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("Viewport", () => {
  it("renders one handle per anchor", () => {
    const shape = parseTrackShape(example);
    const { container } = render(<Viewport shape={shape} />);
    expect(container.querySelectorAll("[data-anchor]").length).toBe(shape.anchors.length);
  });

  it("renders the sampled preview polyline", () => {
    const shape = parseTrackShape(example);
    const { container } = render(<Viewport shape={shape} />);
    expect(container.querySelector("[data-preview]")).toBeTruthy();
  });

  it("renders a reference image behind the generated geometry", () => {
    const shape = parseTrackShape(example);
    const { container } = render(
      <Viewport
        shape={shape}
        referenceImage={{
          href: "data:image/png;base64,QUJD",
          name: "track.png",
          widthPx: 100,
          heightPx: 50,
          x: -10,
          y: -20,
          width: 100,
          height: 50,
          opacity: 0.5,
          visible: true,
        }}
      />,
    );

    const layer = container.querySelector("[data-reference-image]");
    const image = layer?.querySelector("image");
    expect(layer).toBeTruthy();
    expect(image?.getAttribute("href")).toBe("data:image/png;base64,QUJD");
    expect(image?.getAttribute("transform")).toBe("scale(1 -1)");
  });

  it("renders additional layouts as separate previews", () => {
    const shape = parseTrackShape({
      ...example,
      layouts: [
        {
          id: "PitLane",
          label: "Pit Lane",
          kind: "pit_lane",
          closed: false,
          anchors: [
            { id: "pit_a", x: 0, y: 25, z: 0 },
            { id: "pit_b", x: 100, y: 25, z: 0 },
          ],
          segments: [{ id: "pit_seg", type: "line", from: "pit_a", to: "pit_b", samples: 1 }],
        },
      ],
    });
    const { container } = render(<Viewport shape={shape} />);
    expect(container.querySelector('[data-layout-preview="PitLane"]')).toBeTruthy();
  });
});
