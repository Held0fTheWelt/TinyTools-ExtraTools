import type { Diagnostic, PatchProposal } from "@aiagmw/shared";
import { applyOperations, operationDiagnostics } from "../operations/executor";
import { cloneWorkspaceState } from "../stateUtils";
import { detectCycleDiagnostics } from "../validation/cycles";
import type { WorkspaceState } from "../workspace";
import { reindexWorkspace, validateWorkspaceState } from "../workspaceIndex";

export interface PatchSimulationResult {
  proposal: PatchProposal;
  before: WorkspaceState;
  after: WorkspaceState;
  operationErrors: ReturnType<typeof applyOperations>["errors"];
  diagnostics: Diagnostic[];
  applicable: boolean;
}

export function simulatePatch(state: WorkspaceState, proposal: PatchProposal): PatchSimulationResult {
  const before = cloneWorkspaceState(state);
  const after = cloneWorkspaceState(state);
  const { errors } = applyOperations(after, proposal.operations);

  reindexWorkspace(after);
  const referenceDiagnostics = validateWorkspaceState(after);
  const cycleDiagnostics = detectCycleDiagnostics(after.models);
  const diagnostics = [...operationDiagnostics(errors), ...referenceDiagnostics, ...cycleDiagnostics];

  return {
    proposal,
    before,
    after,
    operationErrors: errors,
    diagnostics,
    applicable: errors.length === 0 && !diagnostics.some((diagnostic) => diagnostic.level === "error")
  };
}
