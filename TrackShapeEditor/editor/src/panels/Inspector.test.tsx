import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Inspector } from "./Inspector";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("Inspector segment editing", () => {
  it("edits samples and reports the change", () => {
    const doc = parseTrackShape(example);
    const seg = doc.segments.find((s) => s.type === "bezier")!;
    const onChange = vi.fn();
    render(<Inspector doc={doc} selection={{ kind: "segment", id: seg.id }} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/samples/i), { target: { value: "40" } });
    expect(onChange).toHaveBeenCalled();
  });
});
