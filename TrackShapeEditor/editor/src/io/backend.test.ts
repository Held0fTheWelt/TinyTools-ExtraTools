import { describe, it, expect, vi } from "vitest";
import { makeTauriBackend } from "./backend";

describe("tauri backend", () => {
  it("open() reads the chosen file; save() writes the chosen path", async () => {
    const api = {
      openDialog: vi.fn().mockResolvedValue("/p/track.json"),
      readText: vi.fn().mockResolvedValue('{"x":1}'),
      saveDialog: vi.fn().mockResolvedValue("/p/out.json"),
      writeText: vi.fn().mockResolvedValue(undefined),
    };
    const be = makeTauriBackend(api);
    expect(await be.open()).toEqual({ name: "/p/track.json", text: '{"x":1}' });
    await be.save("out.json", "data");
    expect(api.writeText).toHaveBeenCalledWith("/p/out.json", "data");
  });
});
