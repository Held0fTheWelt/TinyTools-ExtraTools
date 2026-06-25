import { describe, it, expect } from "vitest";
import conf from "../../src-tauri/tauri.conf.json";

describe("tauri config", () => {
  it("ships the built Vite dist and a product name", () => {
    expect((conf as { build: { frontendDist: string }; productName: string }).build.frontendDist).toContain("dist");
    expect((conf as { productName: string }).productName).toMatch(/Track Shape/i);
  });
});
