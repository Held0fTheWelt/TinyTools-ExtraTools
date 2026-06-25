const apiBase = process.env.AIAGMW_API_URL ?? "http://127.0.0.1:3000";

async function callTool(tool: string, args: Record<string, unknown> = {}) {
  const response = await fetch(`${apiBase}/api/agent-tools`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tool, arguments: args })
  });
  const body = (await response.json()) as { ok: boolean; error?: string; result?: unknown };
  if (!response.ok || !body.ok) {
    throw new Error(body.error ?? `${tool} failed`);
  }
  return body.result;
}

async function main() {
  console.log("Agent smoke: workspace_get_info");
  const info = await callTool("workspace_get_info");
  console.log(JSON.stringify(info, null, 2));

  const proposal = {
    schema: "umlpatch.v1" as const,
    id: `proposal.smoke.${Date.now()}`,
    title: "Smoke test note element",
    intent: "Verify agent proposal submit/preview/apply flow.",
    status: "pending" as const,
    risk: "low" as const,
    operations: [
      {
        op: "add_element",
        modelId: "model.inventory",
        element: {
          id: `note.SmokeNote${Date.now()}`,
          kind: "note",
          name: "Smoke Note",
          responsibilities: ["Agent smoke test"],
          properties: [],
          methods: [],
          constraints: [],
          tags: ["smoke"]
        }
      }
    ],
    metadata: { smoke: true }
  };

  console.log("Agent smoke: proposal_submit_patch");
  const submitted = await callTool("proposal_submit_patch", { patch: proposal });
  console.log(JSON.stringify(submitted, null, 2));

  console.log("Agent smoke: proposal_preview_patch");
  const preview = await callTool("proposal_preview_patch", { patch: proposal });
  console.log(JSON.stringify({ applicable: (preview as { applicable?: boolean }).applicable }, null, 2));

  console.log("Agent smoke: proposal_apply_approved without approval (expect failure)");
  try {
    await callTool("proposal_apply_approved", { proposalId: proposal.id });
    throw new Error("Expected apply without approval to fail.");
  } catch (error) {
    console.log("Expected failure:", error instanceof Error ? error.message : error);
  }

  console.log("Agent smoke complete.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
