import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TrackTree } from "./TrackTree";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("TrackTree", () => {
  it("clicking an anchor calls onSelect", () => {
    const doc = parseTrackShape(example);
    const onSelect = vi.fn();
    render(<TrackTree doc={doc} selection={null} onSelect={onSelect} />);
    fireEvent.click(screen.getByText(doc.anchors[0].label ?? doc.anchors[0].id));
    expect(onSelect).toHaveBeenCalledWith({ kind: "anchor", id: doc.anchors[0].id });
  });

  it("keeps the navigation scrollable inside the app layout", () => {
    const doc = parseTrackShape(example);
    render(<TrackTree doc={doc} selection={null} onSelect={vi.fn()} />);
    expect(screen.getByTestId("track-tree")).toHaveStyle({
      overflowY: "auto",
      height: "100%",
    });
  });
});
