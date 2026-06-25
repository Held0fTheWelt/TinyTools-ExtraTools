import { describe, expect, it } from "vitest";
import type { PatchPreviewResponse } from "@aiagmw/shared";
import { buildDiffElementStates, endpointId, formatParameters, nodeClassName, relationLabel, visibilitySymbol } from "./diagramViewModel";

describe("diagram view model helpers", () => {
  it("normalizes cross-model endpoint references for React Flow node ids", () => {
    expect(endpointId("model.inventory#class.ItemDefinition")).toBe("class.ItemDefinition");
    expect(endpointId("class.InventoryComponent")).toBe("class.InventoryComponent");
  });

  it("formats relation labels with names and multiplicities", () => {
    expect(relationLabel({ kind: "association", name: "contains", fromMultiplicity: "1", toMultiplicity: "*" })).toBe(
      "contains 1 .. *"
    );
    expect(relationLabel({ kind: "dependency" })).toBe("dependency");
  });

  it("builds diff states and class names for highlighted diagram nodes", () => {
    const preview: PatchPreviewResponse = {
      proposal: {
        schema: "umlpatch.v1",
        id: "proposal.test",
        title: "Test patch",
        intent: "Exercise diff highlighting.",
        status: "pending",
        operations: []
      },
      applicable: true,
      diagnostics: [],
      diff: {
        addedElements: [{ modelId: "model.inventory", element: { id: "class.New", kind: "class", name: "New" } }],
        removedElements: [{ modelId: "model.inventory", element: { id: "class.Old", kind: "class", name: "Old" } }],
        updatedElements: [
          {
            modelId: "model.inventory",
            elementId: "class.Changed",
            before: { id: "class.Changed", kind: "class", name: "Old Name" },
            after: { id: "class.Changed", kind: "class", name: "New Name" }
          }
        ],
        addedRelations: [],
        removedRelations: [],
        updatedRelations: [],
        addedDiagrams: [],
        updatedDiagrams: [],
        layoutChanges: [],
        affectedModelIds: [],
        affectedDiagramIds: []
      },
      operationErrors: []
    };

    const states = buildDiffElementStates(preview);

    expect(states.get("class.New")).toBe("added");
    expect(states.get("class.Old")).toBe("removed");
    expect(states.get("class.Changed")).toBe("updated");
    expect(nodeClassName({ kind: "interface" }, true, "updated")).toBe("uml-node interface selected diff-updated");
  });

  it("formats UML member details", () => {
    expect(visibilitySymbol("private")).toBe("- ");
    expect(formatParameters([{ name: "id", type: "string" }, { name: "count" }])).toBe("id: string, count");
  });
});
