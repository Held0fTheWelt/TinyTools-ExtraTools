import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Metrics } from "./Metrics";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

describe("Metrics", () => {
  it("shows main length and point count", () => {
    render(<Metrics shape={parseTrackShape(example)} />);
    expect(screen.getByText(/Main Length/i)).toBeInTheDocument();
    expect(screen.getByText(/4098/)).toBeInTheDocument();
  });
});
