import { describe, expect, it } from "vitest";
import type { PatchOperation, WorkspaceIndex } from "@aiagmw/shared";
import type { WorkspaceState } from "../workspace";
import { applyOperations } from "./executor";

const emptyIndex: WorkspaceIndex = {
  models: [],
  diagrams: [],
  proposals: [],
  elementToModel: {},
  elementToDiagrams: {},
  relationToModel: {},
  tags: {}
};

function createTestState(): WorkspaceState {
  return {
    root: "/test",
    manifest: null,
    models: [
      {
        data: {
          schema: "umlmodel.v1",
          id: "model.source",
          name: "Source Model",
          modelType: "class-model",
          elements: [
            {
              id: "class.Alpha",
              kind: "class",
              name: "Alpha",
              tags: ["seed"],
              metadata: { status: "draft", notes: ["existing note"] }
            },
            {
              id: "class.Beta",
              kind: "class",
              name: "Beta",
              tags: []
            }
          ],
          relations: [
            {
              id: "relation.Alpha__association__Beta",
              kind: "association",
              from: "class.Alpha",
              to: "class.Beta",
              tags: ["relation-seed"]
            }
          ],
          metadata: { status: "draft", tags: ["model-seed"] }
        },
        file: "",
        relativePath: ""
      },
      {
        data: {
          schema: "umlmodel.v1",
          id: "model.target",
          name: "Target Model",
          modelType: "class-model",
          elements: [],
          relations: [],
          metadata: {}
        },
        file: "",
        relativePath: ""
      }
    ],
    diagrams: [
      {
        data: {
          schema: "umldiagram.v1",
          id: "diagram.main",
          name: "Main Diagram",
          diagramType: "class",
          modelRefs: ["model.source"],
          elementRefs: ["class.Alpha", "class.Beta"],
          relationRefs: ["relation.Alpha__association__Beta"],
          metadata: { status: "draft", tags: ["diagram-seed"] }
        },
        file: "",
        relativePath: ""
      }
    ],
    layouts: [
      {
        data: {
          schema: "umllayout.v1",
          diagramId: "diagram.main",
          nodes: {
            "class.Alpha": { x: 10, y: 20, width: 120, height: 80 },
            "class.Beta": { x: 200, y: 20, width: 120, height: 80 }
          },
          edges: {
            "relation.Alpha__association__Beta": {
              points: [{ x: 130, y: 60 }, { x: 200, y: 60 }]
            }
          }
        },
        file: "",
        relativePath: ""
      }
    ],
    proposals: [],
    diagnostics: [],
    index: emptyIndex
  };
}

function applySingle(state: WorkspaceState, operation: PatchOperation) {
  return applyOperations(state, [operation]);
}

describe("patch operation executor", () => {
  describe("rename_element", () => {
    it("renames an element without changing its id", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "rename_element",
        modelId: "model.source",
        elementId: "class.Alpha",
        updates: { name: "AlphaRenamed" }
      });

      expect(result.errors).toEqual([]);
      expect(state.models[0]?.data.elements[0]?.name).toBe("AlphaRenamed");
      expect(state.models[0]?.data.elements[0]?.id).toBe("class.Alpha");
    });

    it("fails when name is missing", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "rename_element",
        modelId: "model.source",
        elementId: "class.Alpha"
      });

      expect(result.errors[0]?.message).toMatch(/updates\.name/);
    });
  });

  describe("move_element_to_model", () => {
    it("moves an element and its incident relations to another model", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "move_element_to_model",
        modelId: "model.source",
        elementId: "class.Alpha",
        updates: { targetModelId: "model.target" }
      });

      expect(result.errors).toEqual([]);
      expect(state.models[0]?.data.elements.map((element) => element.id)).toEqual(["class.Beta"]);
      expect(state.models[1]?.data.elements.map((element) => element.id)).toEqual(["class.Alpha"]);
      expect(state.models[0]?.data.relations).toHaveLength(0);
      expect(state.models[1]?.data.relations.map((relation) => relation.id)).toEqual([
        "relation.Alpha__association__Beta"
      ]);
      expect(state.diagrams[0]?.data.modelRefs).toEqual(expect.arrayContaining(["model.source", "model.target"]));
    });

    it("fails when target model is missing", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "move_element_to_model",
        modelId: "model.source",
        elementId: "class.Alpha",
        updates: { targetModelId: "model.missing" }
      });

      expect(result.errors[0]?.message).toMatch(/model.missing/);
    });
  });

  describe("set_edge_route", () => {
    it("updates edge routing points for a relation", () => {
      const state = createTestState();
      const points = [
        { x: 40, y: 50 },
        { x: 180, y: 50 }
      ];
      const result = applySingle(state, {
        op: "set_edge_route",
        diagramId: "diagram.main",
        relationId: "relation.Alpha__association__Beta",
        updates: { points }
      });

      expect(result.errors).toEqual([]);
      expect(state.layouts[0]?.data.edges["relation.Alpha__association__Beta"]?.points).toEqual(points);
    });

    it("fails when relation does not exist", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "set_edge_route",
        diagramId: "diagram.main",
        relationId: "relation.missing",
        updates: { points: [{ x: 1, y: 2 }] }
      });

      expect(result.errors[0]?.message).toMatch(/relation.missing/);
    });
  });

  describe("apply_layout", () => {
    it("merges node and edge layout updates", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "apply_layout",
        diagramId: "diagram.main",
        updates: {
          nodes: {
            "class.Alpha": { x: 99, y: 88, width: 150, height: 90 }
          },
          edges: {
            "relation.Alpha__association__Beta": {
              points: [{ x: 10, y: 10 }, { x: 20, y: 20 }]
            }
          }
        }
      });

      expect(result.errors).toEqual([]);
      expect(state.layouts[0]?.data.nodes["class.Alpha"]).toMatchObject({ x: 99, y: 88, width: 150, height: 90 });
      expect(state.layouts[0]?.data.nodes["class.Beta"]).toMatchObject({ x: 200, y: 20 });
      expect(state.layouts[0]?.data.edges["relation.Alpha__association__Beta"]?.points).toEqual([
        { x: 10, y: 10 },
        { x: 20, y: 20 }
      ]);
    });

    it("fails when no layout payload is provided", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "apply_layout",
        diagramId: "diagram.main"
      });

      expect(result.errors[0]?.message).toMatch(/updates\.nodes/);
    });
  });

  describe("add_note", () => {
    it.each([
      ["element", { op: "add_note", modelId: "model.source", elementId: "class.Alpha", updates: { note: "element note" } }],
      ["relation", { op: "add_note", modelId: "model.source", relationId: "relation.Alpha__association__Beta", updates: { note: "relation note" } }],
      ["diagram", { op: "add_note", diagramId: "diagram.main", updates: { note: "diagram note" } }],
      ["model", { op: "add_note", modelId: "model.source", updates: { note: "model note" } }]
    ] as const)("appends a note to a %s target", (_label, operation) => {
      const state = createTestState();
      const result = applySingle(state, operation);

      expect(result.errors).toEqual([]);
      if ("elementId" in operation && operation.elementId) {
        expect(state.models[0]?.data.elements[0]?.metadata?.notes).toEqual(["existing note", "element note"]);
      } else if ("relationId" in operation && operation.relationId) {
        expect(state.models[0]?.data.relations[0]?.metadata?.notes).toEqual(["relation note"]);
      } else if ("diagramId" in operation && operation.diagramId) {
        expect(state.diagrams[0]?.data.metadata?.notes).toEqual(["diagram note"]);
      } else {
        expect(state.models[0]?.data.metadata?.notes).toEqual(["model note"]);
      }
    });
  });

  describe("add_tag", () => {
    it.each([
      ["element", { op: "add_tag", modelId: "model.source", elementId: "class.Alpha", updates: { tag: "runtime" } }, ["seed", "runtime"]],
      ["relation", { op: "add_tag", modelId: "model.source", relationId: "relation.Alpha__association__Beta", updates: { tag: "critical" } }, ["relation-seed", "critical"]],
      ["diagram", { op: "add_tag", diagramId: "diagram.main", updates: { tag: "reviewed" } }, ["diagram-seed", "reviewed"]],
      ["model", { op: "add_tag", modelId: "model.source", updates: { tag: "architecture" } }, ["model-seed", "architecture"]]
    ] as const)("adds a tag on a %s target", (_label, operation, expectedTags) => {
      const state = createTestState();
      const result = applySingle(state, operation);

      expect(result.errors).toEqual([]);
      if ("elementId" in operation && operation.elementId) {
        expect(state.models[0]?.data.elements[0]?.tags).toEqual(expectedTags);
      } else if ("relationId" in operation && operation.relationId) {
        expect(state.models[0]?.data.relations[0]?.tags).toEqual(expectedTags);
      } else if ("diagramId" in operation && operation.diagramId) {
        expect(state.diagrams[0]?.data.metadata?.tags).toEqual(expectedTags);
      } else {
        expect(state.models[0]?.data.metadata?.tags).toEqual(expectedTags);
      }
    });
  });

  describe("remove_tag", () => {
    it.each([
      ["element", { op: "remove_tag", modelId: "model.source", elementId: "class.Alpha", updates: { tag: "seed" } }],
      ["relation", { op: "remove_tag", modelId: "model.source", relationId: "relation.Alpha__association__Beta", updates: { tag: "relation-seed" } }],
      ["diagram", { op: "remove_tag", diagramId: "diagram.main", updates: { tag: "diagram-seed" } }],
      ["model", { op: "remove_tag", modelId: "model.source", updates: { tag: "model-seed" } }]
    ] as const)("removes a tag from a %s target", (_label, operation) => {
      const state = createTestState();
      const result = applySingle(state, operation);

      expect(result.errors).toEqual([]);
      if ("elementId" in operation && operation.elementId) {
        expect(state.models[0]?.data.elements[0]?.tags).toEqual([]);
      } else if ("relationId" in operation && operation.relationId) {
        expect(state.models[0]?.data.relations[0]?.tags).toEqual([]);
      } else if ("diagramId" in operation && operation.diagramId) {
        expect(state.diagrams[0]?.data.metadata?.tags).toEqual([]);
      } else {
        expect(state.models[0]?.data.metadata?.tags).toEqual([]);
      }
    });
  });

  describe("link_decision", () => {
    it("links a decision reference on an element", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "link_decision",
        modelId: "model.source",
        elementId: "class.Alpha",
        updates: { decisionId: "ADR-PROJ-0001" }
      });

      expect(result.errors).toEqual([]);
      expect(state.models[0]?.data.elements[0]?.metadata?.linkedDecisions).toEqual(["ADR-PROJ-0001"]);
    });

    it("accepts updates.reference as an alias", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "link_decision",
        modelId: "model.source",
        updates: { reference: "ADR-PROJ-0002" }
      });

      expect(result.errors).toEqual([]);
      expect(state.models[0]?.data.metadata?.linkedDecisions).toEqual(["ADR-PROJ-0002"]);
    });
  });

  describe("link_practice", () => {
    it("links a practice reference on a relation", () => {
      const state = createTestState();
      const result = applySingle(state, {
        op: "link_practice",
        modelId: "model.source",
        relationId: "relation.Alpha__association__Beta",
        updates: { practiceId: "practice.boundary-ports" }
      });

      expect(result.errors).toEqual([]);
      expect(state.models[0]?.data.relations[0]?.metadata?.linkedPractices).toEqual(["practice.boundary-ports"]);
    });
  });

  describe("set_status", () => {
    it.each([
      ["element", { op: "set_status", modelId: "model.source", elementId: "class.Alpha", updates: { status: "approved" } }],
      ["relation", { op: "set_status", modelId: "model.source", relationId: "relation.Alpha__association__Beta", updates: { status: "review" } }],
      ["diagram", { op: "set_status", diagramId: "diagram.main", updates: { status: "published" } }],
      ["model", { op: "set_status", modelId: "model.source", updates: { status: "active" } }]
    ] as const)("sets status metadata on a %s target", (_label, operation) => {
      const state = createTestState();
      const result = applySingle(state, operation);

      expect(result.errors).toEqual([]);
      const expectedStatus = operation.updates?.status;
      if ("elementId" in operation && operation.elementId) {
        expect(state.models[0]?.data.elements[0]?.metadata?.status).toBe(expectedStatus);
      } else if ("relationId" in operation && operation.relationId) {
        expect(state.models[0]?.data.relations[0]?.metadata?.status).toBe(expectedStatus);
      } else if ("diagramId" in operation && operation.diagramId) {
        expect(state.diagrams[0]?.data.metadata?.status).toBe(expectedStatus);
      } else {
        expect(state.models[0]?.data.metadata?.status).toBe(expectedStatus);
      }
    });
  });
});
