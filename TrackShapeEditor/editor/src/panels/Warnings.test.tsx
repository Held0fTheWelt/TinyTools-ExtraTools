import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Warnings } from "./Warnings";

describe("Warnings panel", () => {
  it("lists diagnostics and calls onSelect with the target id", () => {
    const onSelect = vi.fn();
    render(
      <Warnings
        items={[
          {
            code: "sharp_corner",
            severity: "warning",
            targetId: "backstretch",
            message: "Sharp corner…",
          },
        ]}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText(/Sharp corner/));
    expect(onSelect).toHaveBeenCalledWith("backstretch");
  });
});
