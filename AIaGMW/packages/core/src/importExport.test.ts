import { describe, expect, it } from "vitest";
import { cp, mkdtemp, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import {
  exportDiagramSource,
  importDiagramAsPatch,
  importDiagramSource,
  parseMermaid,
  parsePlantUml
} from "./importExport";
import { buildImportPatch } from "./import/importPatch";
import { loadWorkspace } from "./workspace";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const schemaDir = path.join(repoRoot, "docs", "Resources", "schemas");
const sampleWorkspace = path.join(repoRoot, "sample-workspace");

const plantUmlFixture = `@startuml
title Billing Import
class Invoice
interface PaymentPort
Invoice ..> PaymentPort : charges
@enduml`;

const mermaidClassFixture = `%% title: Orders Class
classDiagram
class Order
class Customer
Order --> Customer : placed by
`;

describe("importExport golden fixtures", () => {
  it("parses PlantUML class diagram into expected semantic candidate", () => {
    const parsed = parsePlantUml(plantUmlFixture);
    expect(parsed).toMatchObject({
      name: "Billing Import",
      diagramType: "class",
      modelType: "class-model",
      elements: [
        { key: "Invoice", kind: "class", name: "Invoice" },
        { key: "PaymentPort", kind: "interface", name: "PaymentPort" }
      ],
      relations: [
        {
          source: "Invoice",
          target: "PaymentPort",
          kind: "dependency",
          label: "charges"
        }
      ]
    });
  });

  it("builds an import patch proposal from PlantUML without writing workspace files", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-import-patch-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const built = await buildImportPatch(
        { root, schemaDir },
        { format: "plantuml", name: "Billing Import", source: plantUmlFixture }
      );

      expect(built.proposal.schema).toBe("umlpatch.v1");
      expect(built.proposal.status).toBe("pending");
      expect(built.proposal.operations.map((operation) => operation.op)).toEqual(
        expect.arrayContaining(["create_model", "create_diagram", "add_element", "add_relation", "add_to_diagram"])
      );
      expect(built.imported).toEqual({ elements: 2, relations: 1 });
      expect(built.sourceRelativePath).toBe("imports/billing-import.puml");

      const state = await loadWorkspace({ root, schemaDir });
      expect(state.models.some((model) => model.data.name === "Billing Import")).toBe(false);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("parses extended PlantUML kinds aligned with AKDB basics", () => {
    const parsed = parsePlantUml(`@startuml
actor Shopper
usecase Checkout
database OrdersDb
queue OrderEvents
state Pending
participant WebApp
object Cart
Checkout --> OrdersDb
@enduml`);

    expect(parsed.elements.map((element) => [element.name, element.kind, element.metadata?.parsedKind])).toEqual(
      expect.arrayContaining([
        ["Shopper", "actor", undefined],
        ["Checkout", "boundary", "usecase"],
        ["OrdersDb", "node", "database"],
        ["OrderEvents", "service", "queue"],
        ["Pending", "component", "state"],
        ["WebApp", "actor", "participant"],
        ["Cart", "class", "object"]
      ])
    );
    expect(parsed.diagramType).toBe("mixed");
  });

  it("parses Mermaid classDiagram and exports class diagrams as classDiagram", async () => {
    const parsed = parseMermaid(mermaidClassFixture);
    expect(parsed).toMatchObject({
      name: "Orders Class",
      diagramType: "class",
      elements: [
        { key: "Order", kind: "class", name: "Order" },
        { key: "Customer", kind: "class", name: "Customer" }
      ]
    });

    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-import-export-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const imported = await importDiagramSource(
        { root, schemaDir },
        { format: "mermaid", name: "Orders Class", source: mermaidClassFixture }
      );
      expect(imported.imported).toEqual({ elements: 2, relations: 1 });

      const exported = await exportDiagramSource({ root, schemaDir }, imported.diagram.id, "mermaid");
      expect(exported.source).toContain("classDiagram");
      expect(exported.source).not.toContain("flowchart LR");
      await readFile(path.join(root, exported.path), "utf8");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });

  it("submits import as pending proposal via importDiagramAsPatch", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "aiagmw-import-proposal-"));
    try {
      await cp(sampleWorkspace, root, { recursive: true });
      const result = await importDiagramAsPatch(
        { root, schemaDir },
        { format: "plantuml", name: "Billing Import", source: plantUmlFixture },
        true
      );

      expect(result.summary?.status).toBe("pending");
      expect(result.applicable).toBe(true);

      const state = await loadWorkspace({ root, schemaDir });
      expect(state.proposals.some((proposal) => proposal.data.id === result.proposal.id)).toBe(true);
      expect(state.models.some((model) => model.data.name === "Billing Import")).toBe(false);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
