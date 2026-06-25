import { describe, expect, it } from "vitest";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { applyPatch, approveProposal, previewPatch } from "./applyPatch";
import { loadWorkspace } from "../workspace";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../../..");
const schemaDir = path.join(repoRoot, "docs", "Resources", "schemas");
const sampleWorkspace = path.join(repoRoot, "sample-workspace");

describe("patch engine", () => {
  it("previews the sample proposal without writing files", async () => {
    const preview = await previewPatch({ root: sampleWorkspace, schemaDir }, "proposal.inventory.persistence-port");
    expect(preview.applicable).toBe(true);
    expect(preview.diff.addedElements).toHaveLength(1);
    expect(preview.diff.addedRelations).toHaveLength(1);
    expect(preview.diff.layoutChanges.length).toBeGreaterThan(0);

    const state = await loadWorkspace({ root: sampleWorkspace, schemaDir });
    expect(state.models[0]?.data.elements.some((element) => element.id === "interface.IInventoryPersistencePort")).toBe(false);
  });

  it("applies an approved proposal and records history", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-patch-"));
    try {
      const { cp } = await import("node:fs/promises");
      await cp(sampleWorkspace, root, { recursive: true });

      const approval = {
        approvedBy: "test-user",
        approvedAt: new Date().toISOString(),
        approvalNote: "Test approval",
        validationStatus: "passed"
      };

      await approveProposal({ root, schemaDir }, "proposal.inventory.persistence-port", approval);
      const result = await applyPatch({ root, schemaDir }, "proposal.inventory.persistence-port", "test-user");

      expect(result.proposal.status).toBe("accepted");
      expect(result.history.proposalId).toBe("proposal.inventory.persistence-port");

      const state = await loadWorkspace({ root, schemaDir });
      expect(state.models[0]?.data.elements.some((element) => element.id === "interface.IInventoryPersistencePort")).toBe(true);
      expect(state.proposals.some((proposal) => proposal.data.status === "accepted")).toBe(true);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("rejects apply without approval metadata", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-patch-"));
    try {
      const { cp } = await import("node:fs/promises");
      await cp(sampleWorkspace, root, { recursive: true });

      await expect(applyPatch({ root, schemaDir }, "proposal.inventory.persistence-port", "test-user")).rejects.toThrow(
        /approval record/i
      );
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
