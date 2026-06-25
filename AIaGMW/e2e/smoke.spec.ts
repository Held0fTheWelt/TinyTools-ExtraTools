import { test, expect } from "@playwright/test";

test("backend health responds", async ({ request }) => {
  const response = await request.get("/api/health");
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.name).toBe("AIaGMW backend");
});

test("workspace info loads sample workspace", async ({ request }) => {
  const response = await request.get("/api/workspace/info");
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.index.diagrams.length).toBeGreaterThan(0);
});

test("agent model_validate tool", async ({ request }) => {
  const response = await request.post("/api/agent-tools", {
    data: { tool: "model_validate", arguments: {} }
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.ok).toBe(true);
});
