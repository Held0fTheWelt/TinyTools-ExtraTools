import { describe, expect, it } from "vitest";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { cp, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import {
  addElementToDiagram,
  addRelationToDiagram,
  createDiagram,
  createModel,
  createRelationInDiagram,
  deleteElementFromModel,
  deleteRelationFromModel,
  getDiagramDetail,
  loadWorkspace,
  removeElementFromDiagram,
  removeRelationFromDiagram,
  searchModel,
  updateRelation
} from "./workspace";
import { exportDiagramSource, importDiagramSource } from "./importExport";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const workspaceRoot = path.join(repoRoot, "sample-workspace");
const schemaDir = path.join(repoRoot, "docs", "Resources", "schemas");

describe("workspace loader", () => {
  it("loads the sample workspace without hard errors", async () => {
    const state = await loadWorkspace({ root: workspaceRoot, schemaDir });
    expect(state.manifest?.id).toBe("workspace.example");
    expect(state.models).toHaveLength(1);
    expect(state.diagrams).toHaveLength(1);
    expect(state.diagnostics.filter((diagnostic) => diagnostic.level === "error")).toHaveLength(0);
  });

  it("resolves diagram detail from semantic model and layout", async () => {
    const state = await loadWorkspace({ root: workspaceRoot, schemaDir });
    const detail = getDiagramDetail(state, "diagram.inventory.class");
    expect(detail?.elements.map((element) => element.id)).toContain("class.InventoryComponent");
    expect(detail?.layout.nodes["class.InventoryComponent"]?.x).toEqual(expect.any(Number));
  });

  it("searches semantic elements", async () => {
    const state = await loadWorkspace({ root: workspaceRoot, schemaDir });
    const results = searchModel(state, "InventoryComponent");
    expect(results.some((result) => result.id === "class.InventoryComponent")).toBe(true);
  });

  it("creates relations as semantic model data and diagram membership", async () => {
    const root = await copySampleWorkspace();
    try {
      const detail = await createRelationInDiagram({ root, schemaDir }, "diagram.inventory.class", {
        kind: "dependency",
        from: "class.ItemDefinition",
        to: "class.InventoryComponent"
      });

      expect(detail.relations.some((relation) => relation.kind === "dependency")).toBe(true);
      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      const diagram = state.diagrams.find((entry) => entry.data.id === "diagram.inventory.class");
      const created = model?.data.relations.find((relation) => relation.kind === "dependency");
      expect(created).toBeTruthy();
      expect(diagram?.data.relationRefs).toContain(created?.id);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("creates a new diagram with a separate layout file", async () => {
    const root = await copySampleWorkspace();
    try {
      const diagram = await createDiagram(
        { root, schemaDir },
        {
          name: "Inventory Alternate",
          diagramType: "class",
          modelRefs: ["model.inventory"]
        }
      );

      const state = await loadWorkspace({ root, schemaDir });
      expect(state.diagrams.map((entry) => entry.data.id)).toContain(diagram.id);
      expect(state.layouts.map((entry) => entry.data.diagramId)).toContain(diagram.id);
      expect(diagram.elementRefs).toHaveLength(0);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("creates a new semantic model file", async () => {
    const root = await copySampleWorkspace();
    try {
      const model = await createModel(
        { root, schemaDir },
        {
          name: "Crafting System",
          modelType: "class-model"
        }
      );

      const state = await loadWorkspace({ root, schemaDir });
      expect(model.id).toBe("model.crafting-system");
      expect(state.models.map((entry) => entry.data.id)).toContain(model.id);
      expect(model.elements).toHaveLength(0);
      expect(model.relations).toHaveLength(0);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("can remove an element from a diagram without deleting semantic data", async () => {
    const root = await copySampleWorkspace();
    try {
      const detail = await removeElementFromDiagram({ root, schemaDir }, "diagram.inventory.class", "class.ItemDefinition");
      expect(detail.elements.map((element) => element.id)).not.toContain("class.ItemDefinition");

      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      const layout = state.layouts.find((entry) => entry.data.diagramId === "diagram.inventory.class");
      expect(model?.data.elements.map((element) => element.id)).toContain("class.ItemDefinition");
      expect(layout?.data.edges["relation.InventoryComponent__association__ItemDefinition"]).toBeUndefined();
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("can add an existing semantic element back to a diagram", async () => {
    const root = await copySampleWorkspace();
    try {
      await removeElementFromDiagram({ root, schemaDir }, "diagram.inventory.class", "class.ItemDefinition");
      const detail = await addElementToDiagram({ root, schemaDir }, "diagram.inventory.class", {
        elementId: "class.ItemDefinition",
        x: 420,
        y: 240
      });

      expect(detail.elements.map((element) => element.id)).toContain("class.ItemDefinition");
      expect(detail.layout.nodes["class.ItemDefinition"]).toMatchObject({ x: 420, y: 240 });

      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      expect(model?.data.elements.map((element) => element.id)).toContain("class.ItemDefinition");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("deletes an element from the model and cleans diagram references", async () => {
    const root = await copySampleWorkspace();
    try {
      await deleteElementFromModel({ root, schemaDir }, "model.inventory", "class.ItemDefinition");
      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      const diagram = state.diagrams.find((entry) => entry.data.id === "diagram.inventory.class");

      expect(model?.data.elements.map((element) => element.id)).not.toContain("class.ItemDefinition");
      expect(model?.data.relations).toHaveLength(0);
      expect(diagram?.data.elementRefs).not.toContain("class.ItemDefinition");
      expect(diagram?.data.relationRefs).toHaveLength(0);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("updates a relation in the semantic model", async () => {
    const root = await copySampleWorkspace();
    try {
      const relation = await updateRelation(
        { root, schemaDir },
        "model.inventory",
        "relation.InventoryComponent__association__ItemDefinition",
        {
          kind: "dependency",
          name: "depends on item data",
          tags: ["edited"]
        }
      );

      expect(relation.kind).toBe("dependency");
      expect(relation.name).toBe("depends on item data");
      expect(relation.tags).toContain("edited");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("can remove a relation from a diagram without deleting semantic data", async () => {
    const root = await copySampleWorkspace();
    try {
      const relationId = "relation.InventoryComponent__association__ItemDefinition";
      const detail = await removeRelationFromDiagram({ root, schemaDir }, "diagram.inventory.class", relationId);
      expect(detail.relations.map((relation) => relation.id)).not.toContain(relationId);

      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      expect(model?.data.relations.map((relation) => relation.id)).toContain(relationId);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("can add an existing semantic relation back to a diagram with its endpoints", async () => {
    const root = await copySampleWorkspace();
    try {
      const relationId = "relation.InventoryComponent__association__ItemDefinition";
      await removeElementFromDiagram({ root, schemaDir }, "diagram.inventory.class", "class.ItemDefinition");

      const detail = await addRelationToDiagram({ root, schemaDir }, "diagram.inventory.class", {
        relationId,
        x: 360,
        y: 280
      });

      expect(detail.elements.map((element) => element.id)).toEqual(
        expect.arrayContaining(["class.InventoryComponent", "class.ItemDefinition"])
      );
      expect(detail.relations.map((relation) => relation.id)).toContain(relationId);
      expect(detail.layout.nodes["class.ItemDefinition"]).toMatchObject({ x: 680, y: 280 });

      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      expect(model?.data.relations.map((relation) => relation.id)).toContain(relationId);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("deletes a relation from the model and cleans diagram references", async () => {
    const root = await copySampleWorkspace();
    try {
      const relationId = "relation.InventoryComponent__association__ItemDefinition";
      await deleteRelationFromModel({ root, schemaDir }, "model.inventory", relationId);
      const state = await loadWorkspace({ root, schemaDir });
      const model = state.models.find((entry) => entry.data.id === "model.inventory");
      const diagram = state.diagrams.find((entry) => entry.data.id === "diagram.inventory.class");

      expect(model?.data.relations.map((relation) => relation.id)).not.toContain(relationId);
      expect(diagram?.data.relationRefs).not.toContain(relationId);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("imports PlantUML as a new semantic model, diagram, layout, and preserved source", async () => {
    const root = await copySampleWorkspace();
    try {
      const result = await importDiagramSource(
        { root, schemaDir },
        {
          format: "plantuml",
          name: "Billing Import",
          source: `@startuml
title Billing Import
class Invoice
interface PaymentPort
Invoice ..> PaymentPort : charges
@enduml`
        }
      );

      const state = await loadWorkspace({ root, schemaDir });
      const detail = getDiagramDetail(state, result.diagram.id);

      expect(result.imported).toEqual({ elements: 2, relations: 1 });
      expect(result.sourcePath).toBe("imports/billing-import.puml");
      expect(state.models.map((entry) => entry.data.id)).toContain(result.model.id);
      expect(detail?.elements.map((element) => element.name)).toEqual(expect.arrayContaining(["Invoice", "PaymentPort"]));
      expect(detail?.relations[0]?.kind).toBe("dependency");
      expect(detail?.layout.nodes[result.model.elements[0]?.id ?? ""]).toMatchObject({ x: 120, y: 120 });
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("exports the selected diagram as PlantUML and Mermaid files", async () => {
    const root = await copySampleWorkspace();
    try {
      const plantUml = await exportDiagramSource({ root, schemaDir }, "diagram.inventory.class", "plantuml");
      const mermaid = await exportDiagramSource({ root, schemaDir }, "diagram.inventory.class", "mermaid");

      expect(plantUml.path).toBe("exports/diagram.inventory.class.puml");
      expect(plantUml.source).toContain("@startuml");
      expect(plantUml.source).toContain("InventoryComponent");
      expect(mermaid.path).toBe("exports/diagram.inventory.class.mmd");
      expect(mermaid.source).toContain("classDiagram");
      expect(mermaid.source).toContain("Inventory Class Diagram");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});

async function copySampleWorkspace(): Promise<string> {
  const root = await mkdtemp(path.join(tmpdir(), "aiagmw-workspace-"));
  await cp(workspaceRoot, root, { recursive: true });
  return root;
}
