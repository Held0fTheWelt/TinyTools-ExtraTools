import { describe, expect, it } from "vitest";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SchemaValidator, type SchemaKind } from "./schemaValidation";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const schemaDir = path.join(repoRoot, "docs", "Resources", "schemas");

const fileToKind: Array<{ pattern: RegExp; kind: SchemaKind }> = [
  { pattern: /workspace\.json$/, kind: "workspace" },
  { pattern: /\.umlmodel\.json$/, kind: "model" },
  { pattern: /\.diagram\.json$/, kind: "diagram" },
  { pattern: /\.layout\.json$/, kind: "layout" },
  { pattern: /\.patch\.json$/, kind: "patch" }
];

async function collectJsonFiles(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectJsonFiles(fullPath)));
    } else if (entry.isFile() && entry.name.endsWith(".json")) {
      files.push(fullPath);
    }
  }
  return files.sort();
}

function kindForFile(file: string): SchemaKind | null {
  for (const { pattern, kind } of fileToKind) {
    if (pattern.test(file)) {
      return kind;
    }
  }
  return null;
}

describe("schema contract tests", () => {
  it("validates all example and sample-workspace JSON files against schemas", async () => {
    const validator = await SchemaValidator.create(schemaDir);
    const dirs = [
      path.join(repoRoot, "docs", "Resources", "examples"),
      path.join(repoRoot, "sample-workspace")
    ];

    for (const dir of dirs) {
      const files = await collectJsonFiles(dir);
      expect(files.length).toBeGreaterThan(0);

      for (const file of files) {
        const kind = kindForFile(file);
        if (!kind) {
          continue;
        }
        const raw = await readFile(file, "utf8");
        const value = JSON.parse(raw) as unknown;
        const relativePath = path.relative(repoRoot, file).replaceAll(path.sep, "/");
        const diagnostics = validator.validate(kind, value, relativePath);
        expect(diagnostics, `${relativePath} should validate as ${kind}`).toEqual([]);
      }
    }
  });

  it("validates sample patch operations against patch schema enum", async () => {
    const validator = await SchemaValidator.create(schemaDir);
    const patchFile = path.join(
      repoRoot,
      "sample-workspace",
      "proposals",
      "pending",
      "decouple_inventory_persistence.patch.json"
    );
    const raw = await readFile(patchFile, "utf8");
    const patch = JSON.parse(raw) as { operations: Array<{ op: string }> };
    const diagnostics = validator.validate("patch", patch, "sample-workspace/proposals/pending/decouple_inventory_persistence.patch.json");
    expect(diagnostics).toEqual([]);
    expect(patch.operations.map((op) => op.op)).toEqual([
      "add_element",
      "add_relation",
      "add_to_diagram",
      "set_node_position"
    ]);
  });
});
