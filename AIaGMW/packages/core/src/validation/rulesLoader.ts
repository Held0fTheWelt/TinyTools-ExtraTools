import { readFile } from "node:fs/promises";
import path from "node:path";
import { safeJoin } from "../workspacePaths";

export interface ForbiddenDependencyRule {
  fromTag: string;
  toTag: string;
  severity?: "error" | "warning" | "info" | "suggestion";
}

export interface ArchitectureRules {
  forbiddenDependencies?: ForbiddenDependencyRule[];
  maxResponsibilitiesPerClass?: number;
  allowCrossModelRelations?: boolean;
}

const defaultRules: ArchitectureRules = {
  forbiddenDependencies: [],
  allowCrossModelRelations: true
};

export async function loadArchitectureRules(workspaceRoot: string): Promise<ArchitectureRules> {
  const rulesFile = safeJoin(path.resolve(workspaceRoot), ".umlworkspace", "rules.json");

  try {
    const raw = await readFile(rulesFile, "utf8");
    const parsed = JSON.parse(raw) as ArchitectureRules;
    return {
      ...defaultRules,
      ...parsed,
      forbiddenDependencies: parsed.forbiddenDependencies ?? defaultRules.forbiddenDependencies
    };
  } catch {
    return defaultRules;
  }
}
