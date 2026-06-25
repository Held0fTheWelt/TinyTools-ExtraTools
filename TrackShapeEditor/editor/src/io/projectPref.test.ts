import { describe, it, expect } from "vitest";
import { loadProjectFolder, saveProjectFolder, type PrefStore } from "./projectPref";

function memStore(): PrefStore {
  const m = new Map<string, string>();
  return { get: async (k) => m.get(k) ?? null, set: async (k, v) => void m.set(k, v) };
}

describe("projectPref", () => {
  it("persists and reloads the project folder", async () => {
    const s = memStore();
    expect(await loadProjectFolder(s)).toBeNull();
    await saveProjectFolder(s, "/projects/tracks");
    expect(await loadProjectFolder(s)).toBe("/projects/tracks");
  });
});
