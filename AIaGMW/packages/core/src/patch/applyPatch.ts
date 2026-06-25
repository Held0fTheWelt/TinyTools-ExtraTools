import type {
  DiagramSummary,
  ModelSummary,
  PatchProposal,
  ProposalSummary,
  UmlDiagram,
  WorkspaceIndex
} from "@aiagmw/shared";
import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { generateDiff } from "./generateDiff";
import { simulatePatch } from "./simulatePatch";
import { runTransaction } from "../transaction";
import type { LoadWorkspaceOptions, WorkspaceState } from "../workspace";
import { loadWorkspace } from "../workspace";
import { relativePath, safeJoin, sanitizeFileName } from "../workspacePaths";

export interface ApprovalRecord {
  approvedBy: string;
  approvedAt: string;
  approvalNote?: string;
  validationStatus?: string;
}

export interface PatchHistoryRecord {
  schema: "umlhistory.v1";
  id: string;
  type: "patch_applied";
  proposalId: string;
  title: string;
  appliedAt: string;
  appliedBy: string;
  approval: ApprovalRecord;
  operationCount: number;
}

export interface ApplyPatchResult {
  proposal: ProposalSummary;
  history: PatchHistoryRecord;
  diff: ReturnType<typeof generateDiff>;
}

export async function applyPatch(
  options: LoadWorkspaceOptions,
  proposalId: string,
  appliedBy = "user"
): Promise<ApplyPatchResult> {
  const state = await loadWorkspace(options);
  const proposalEntry = state.proposals.find((entry) => entry.data.id === proposalId);
  if (!proposalEntry) {
    throw new Error(`Proposal ${proposalId} was not found.`);
  }

  const metadata = proposalEntry.data.metadata ?? {};
  const storedApproval = metadata.approval as ApprovalRecord | undefined;
  if (!storedApproval) {
    throw new Error(`Proposal ${proposalId} has no approval record.`);
  }

  const simulation = simulatePatch(state, proposalEntry.data);
  if (!simulation.applicable) {
    const messages = simulation.diagnostics.map((diagnostic) => diagnostic.message).join("; ");
    throw new Error(`Patch is not applicable: ${messages}`);
  }

  const diff = generateDiff(simulation.before, simulation.after, proposalEntry.data);
  const writes = collectWrites(simulation.before, simulation.after);
  await runTransaction(writes);

  const root = path.resolve(options.root);
  const acceptedDir = safeJoin(root, "proposals", "accepted");
  await mkdir(acceptedDir, { recursive: true });
  const targetFile = safeJoin(acceptedDir, path.basename(proposalEntry.file));
  proposalEntry.data.status = "accepted";
  proposalEntry.data.metadata = {
    ...proposalEntry.data.metadata,
    approval: storedApproval,
    appliedAt: new Date().toISOString(),
    appliedBy
  };
  await writeJson(proposalEntry.file, proposalEntry.data);
  await rename(proposalEntry.file, targetFile);

  const history = await writeHistoryRecord(options, proposalEntry.data, storedApproval, appliedBy);

  return {
    proposal: {
      id: proposalEntry.data.id,
      title: proposalEntry.data.title,
      status: "accepted",
      risk: proposalEntry.data.risk,
      path: relativePath(root, targetFile),
      operationCount: proposalEntry.data.operations.length
    },
    history,
    diff
  };
}

export async function approveProposal(
  options: LoadWorkspaceOptions,
  proposalId: string,
  approval: ApprovalRecord
): Promise<ProposalSummary> {
  const state = await loadWorkspace(options);
  const proposal = state.proposals.find((entry) => entry.data.id === proposalId);
  if (!proposal) {
    throw new Error(`Proposal ${proposalId} was not found.`);
  }

  proposal.data.metadata = {
    ...proposal.data.metadata,
    approval
  };
  await writeJson(proposal.file, proposal.data);

  return {
    id: proposal.data.id,
    title: proposal.data.title,
    status: proposal.data.status,
    risk: proposal.data.risk,
    path: proposal.relativePath,
    operationCount: proposal.data.operations.length
  };
}

export async function previewPatch(options: LoadWorkspaceOptions, proposalId: string) {
  const state = await loadWorkspace(options);
  const proposal = state.proposals.find((entry) => entry.data.id === proposalId);
  if (!proposal) {
    throw new Error(`Proposal ${proposalId} was not found.`);
  }

  const simulation = simulatePatch(state, proposal.data);
  const diff = generateDiff(simulation.before, simulation.after, proposal.data);
  return {
    proposal: proposal.data,
    applicable: simulation.applicable,
    diagnostics: simulation.diagnostics,
    diff,
    operationErrors: simulation.operationErrors
  };
}

function collectWrites(before: WorkspaceState, after: WorkspaceState) {
  const writes: Array<{ file: string; data: unknown }> = [];

  for (const afterModel of after.models) {
    const beforeModel = before.models.find((entry) => entry.data.id === afterModel.data.id);
    if (!beforeModel || JSON.stringify(beforeModel.data) !== JSON.stringify(afterModel.data)) {
      if (afterModel.file) {
        writes.push({ file: afterModel.file, data: afterModel.data });
      }
    }
  }

  for (const afterDiagram of after.diagrams) {
    const beforeDiagram = before.diagrams.find((entry) => entry.data.id === afterDiagram.data.id);
    if (!beforeDiagram || JSON.stringify(beforeDiagram.data) !== JSON.stringify(afterDiagram.data)) {
      if (afterDiagram.file) {
        writes.push({ file: afterDiagram.file, data: afterDiagram.data });
      }
    }
  }

  for (const afterLayout of after.layouts) {
    const beforeLayout = before.layouts.find((entry) => entry.data.diagramId === afterLayout.data.diagramId);
    if (!beforeLayout || JSON.stringify(beforeLayout.data) !== JSON.stringify(afterLayout.data)) {
      if (afterLayout.file) {
        writes.push({ file: afterLayout.file, data: afterLayout.data });
      }
    }
  }

  return writes;
}

async function writeHistoryRecord(
  options: LoadWorkspaceOptions,
  proposal: PatchProposal,
  approval: ApprovalRecord,
  appliedBy: string
): Promise<PatchHistoryRecord> {
  const state = await loadWorkspace(options);
  const historyDir = safeJoin(state.root, state.manifest?.paths.history ?? "history");
  await mkdir(historyDir, { recursive: true });
  const id = `history.${sanitizeFileName(proposal.id)}.${Date.now()}`;
  const record: PatchHistoryRecord = {
    schema: "umlhistory.v1",
    id,
    type: "patch_applied",
    proposalId: proposal.id,
    title: proposal.title,
    appliedAt: new Date().toISOString(),
    appliedBy,
    approval,
    operationCount: proposal.operations.length
  };
  await writeJson(safeJoin(historyDir, `${sanitizeFileName(id)}.json`), record);
  return record;
}

async function writeJson(file: string, value: unknown): Promise<void> {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function summarizeModels(index: WorkspaceIndex): ModelSummary[] {
  return index.models;
}

export function summarizeDiagrams(index: WorkspaceIndex): DiagramSummary[] {
  return index.diagrams;
}
