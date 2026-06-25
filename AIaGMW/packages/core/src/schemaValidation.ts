import Ajv2020, { type ErrorObject, type ValidateFunction } from "ajv/dist/2020.js";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Diagnostic } from "@aiagmw/shared";

export type SchemaKind = "workspace" | "model" | "diagram" | "layout" | "patch";

const schemaFiles: Record<SchemaKind, string> = {
  workspace: "workspace.schema.json",
  model: "model.schema.json",
  diagram: "diagram.schema.json",
  layout: "layout.schema.json",
  patch: "patch.schema.json"
};

export class SchemaValidator {
  private constructor(private readonly validators: Map<SchemaKind, ValidateFunction>) {}

  static async create(schemaDir: string): Promise<SchemaValidator> {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    const validators = new Map<SchemaKind, ValidateFunction>();

    for (const [kind, fileName] of Object.entries(schemaFiles) as Array<[SchemaKind, string]>) {
      const filePath = path.join(schemaDir, fileName);
      const raw = await readFile(filePath, "utf8");
      const schema = JSON.parse(raw) as Record<string, unknown>;
      validators.set(kind, ajv.compile(schema));
    }

    return new SchemaValidator(validators);
  }

  validate(kind: SchemaKind, value: unknown, file?: string): Diagnostic[] {
    const validate = this.validators.get(kind);
    if (!validate) {
      return [
        {
          level: "error",
          code: "schema.validator_missing",
          message: `No validator is registered for ${kind}.`,
          file,
          category: "schema"
        }
      ];
    }

    if (validate(value)) {
      return [];
    }

    return formatAjvErrors(validate.errors ?? [], file);
  }
}

function formatAjvErrors(errors: ErrorObject[], file?: string): Diagnostic[] {
  return errors.map((error) => {
    const location = error.instancePath || "/";
    return {
      level: "error",
      code: `schema.${error.keyword}`,
      message: `${location} ${error.message ?? "is invalid"}`,
      file,
      category: "schema"
    };
  });
}
