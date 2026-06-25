import type { Diagnostic, PatchProposal } from "@aiagmw/shared";
import { SchemaValidator } from "../schemaValidation";
import type { LoadWorkspaceOptions } from "../workspace";

export async function parsePatch(
  options: LoadWorkspaceOptions,
  proposal: PatchProposal
): Promise<{ proposal: PatchProposal; diagnostics: Diagnostic[] }> {
  const validator = await SchemaValidator.create(options.schemaDir);
  const diagnostics = validator.validate("patch", proposal);
  if (diagnostics.some((diagnostic) => diagnostic.level === "error")) {
    throw new Error(`Patch proposal is invalid: ${diagnostics.map((diagnostic) => diagnostic.message).join("; ")}`);
  }
  return { proposal, diagnostics };
}
