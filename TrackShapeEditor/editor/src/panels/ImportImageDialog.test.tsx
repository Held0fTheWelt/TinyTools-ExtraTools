import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ImportImageDialog } from "./ImportImageDialog";
import type { TraceClient } from "../io/traceClient";
import example from "../../test/fixtures/daytona_shape.example.json";

class MockFileReader {
  result: string | null = null;
  onload: null | (() => void) = null;
  onerror: null | (() => void) = null;
  readAsDataURL() {
    this.result = "data:image/png;base64,QUJD";
    this.onload?.();
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
});

function setFile(container: HTMLElement) {
  const input = container.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File([new Uint8Array([1, 2, 3])], "oval.png", { type: "image/png" });
  fireEvent.change(input, { target: { files: [file] } });
}

function disableColorMasking() {
  fireEvent.click(screen.getByLabelText("Use track color"));
}

test("shows a validation error when no file is chosen", () => {
  const client: TraceClient = { trace: vi.fn() };
  render(<ImportImageDialog onImport={vi.fn()} onClose={vi.fn()} client={client} />);
  fireEvent.click(screen.getByRole("button", { name: "Load" }));
  expect(screen.getByRole("alert").textContent).toMatch(/choose an image/i);
  expect(client.trace).not.toHaveBeenCalled();
});

test("traces and imports a parsed, named shape on success", async () => {
  vi.stubGlobal("FileReader", MockFileReader);
  const onImport = vi.fn();
  const tracedShape = {
    ...example,
    metadata: {
      import: {
        image_size_px: [100, 50],
        image_transform: {
          world_rect: { x: -10, y: -20, width: 100, height: 50 },
        },
      },
    },
  };
  const trace = vi.fn().mockResolvedValue({ shape: tracedShape });

  const { container } = render(
    <ImportImageDialog onImport={onImport} onClose={vi.fn()} client={{ trace }} />,
  );
  setFile(container);
  disableColorMasking();
  fireEvent.click(screen.getByRole("button", { name: "Load" }));

  await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1));
  const [shape, name, referenceImage] = onImport.mock.calls[0];
  expect(shape.schema).toBe("track_shape.v1");
  expect(name).toBe("oval.json");
  expect(referenceImage).toMatchObject({
    href: "data:image/png;base64,QUJD",
    name: "oval.png",
    widthPx: 100,
    heightPx: 50,
    x: -10,
    y: -20,
    width: 100,
    height: 50,
  });
  expect(trace).toHaveBeenCalledWith(
    expect.objectContaining({ filename: "oval.png", target_length_m: 4023 }),
  );
});

test("surfaces a tracer error message", async () => {
  vi.stubGlobal("FileReader", MockFileReader);
  const trace = vi.fn().mockResolvedValue({ error: "traced path too short" });

  const { container } = render(
    <ImportImageDialog onImport={vi.fn()} onClose={vi.fn()} client={{ trace }} />,
  );
  setFile(container);
  disableColorMasking();
  fireEvent.click(screen.getByRole("button", { name: "Load" }));

  await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/traced path too short/));
});

test("adds preview clicks as trace guide points", async () => {
  vi.stubGlobal("FileReader", MockFileReader);
  const tracedShape = {
    ...example,
    metadata: {
      import: {
        image_size_px: [100, 50],
        image_transform: {
          world_rect: { x: 0, y: 0, width: 100, height: 50 },
        },
      },
    },
  };
  const trace = vi.fn().mockResolvedValue({ shape: tracedShape });

  const { container } = render(
    <ImportImageDialog onImport={vi.fn()} onClose={vi.fn()} client={{ trace }} />,
  );
  setFile(container);
  disableColorMasking();
  const preview = await screen.findByTestId("image-import-preview");
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));

  await waitFor(() => expect(trace).toHaveBeenCalledTimes(1));
  Object.defineProperty(preview, "getBoundingClientRect", {
    value: () => ({
      left: 0,
      top: 0,
      right: 200,
      bottom: 100,
      width: 200,
      height: 100,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
  fireEvent.click(preview, { clientX: 50, clientY: 25 });

  await waitFor(() => expect(trace).toHaveBeenCalledTimes(2));
  expect(trace.mock.calls[1][0]).toMatchObject({
    guide_points_px: [{ x: 25, y: 12.5 }],
  });
});

test("smooths the preview before importing", async () => {
  vi.stubGlobal("FileReader", MockFileReader);
  const onImport = vi.fn();
  const tracedShape = {
    ...example,
    closed: false,
    anchors: [
      { id: "a", x: 0, y: 0 },
      { id: "b", x: 30, y: 0 },
      { id: "c", x: 30, y: 30 },
    ],
    segments: [
      { id: "s1", type: "line", from: "a", to: "b" },
      { id: "s2", type: "line", from: "b", to: "c" },
    ],
    metadata: {
      import: {
        image_size_px: [100, 50],
        image_transform: {
          world_rect: { x: 0, y: 0, width: 100, height: 50 },
        },
      },
    },
  };
  const trace = vi.fn().mockResolvedValue({ shape: tracedShape });

  const { container } = render(
    <ImportImageDialog onImport={onImport} onClose={vi.fn()} client={{ trace }} />,
  );
  setFile(container);
  disableColorMasking();
  await screen.findByTestId("image-import-preview");
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));
  await waitFor(() => expect(trace).toHaveBeenCalledTimes(1));

  fireEvent.click(screen.getByRole("button", { name: "Smooth" }));
  fireEvent.click(screen.getByRole("button", { name: "Load" }));

  await waitFor(() => expect(onImport).toHaveBeenCalledTimes(1));
  const [shape] = onImport.mock.calls[0];
  expect(shape.segments.every((s: { type: string }) => s.type === "bezier")).toBe(true);
  expect(shape.metadata.smoothing).toMatchObject({ method: "cleaned_c1_tangent_handles" });
});
